"""Nothing/CMF NTAPP RFCOMM protocol driver.

Includes read operations and explicitly supported device configuration commands.
"""
import socket
import struct
import time

MODES = {1: 'ANC High', 2: 'ANC Medium', 3: 'ANC Low', 4: 'Adaptive ANC', 5: 'Off', 7: 'Transparency'}
COMPONENTS = {2: 'left', 3: 'right', 4: 'case', 6: 'headset'}

def crc16(data):
    crc = 0xffff
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xa001) if crc & 1 else crc >> 1
    return crc & 0xffff

def frame(command):
    body = struct.pack('<BHHH', 0x55, 0x0160, command | (0xc0 << 8), 0) + b'\x01'
    return body + struct.pack('<H', crc16(body))

def extract(buf):
    out = []
    while buf:
        try:
            start = buf.index(0x55)
        except ValueError:
            buf.clear(); break
        if start:
            del buf[:start]
        if len(buf) < 8:
            break
        _, ctrl, wire, length = struct.unpack_from('<BHHH', buf)
        total = 8 + length + (2 if ctrl & 0x20 else 0)
        if total > 8192 or total < 8:
            del buf[0]; continue
        if len(buf) < total:
            break
        raw = bytes(buf[:total]); del buf[:total]
        if ctrl & 0x20 and struct.unpack_from('<H', raw, 8 + length)[0] != crc16(raw[:8 + length]):
            continue
        out.append((wire & 0xff, wire >> 8, raw[8:8 + length]))
    return out

def query(address, channel=16, wait=1.8):
    """Return available readings. Only GET frames are transmitted."""
    result = {'battery': {}, 'anc': None, 'latency': None}
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
        sock.settimeout(4)
        sock.connect((address, channel))
        for cmd in (0x07, 0x1e, 0x41):
            sock.sendall(frame(cmd))
        buf = bytearray()
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            sock.settimeout(max(.05, deadline - time.monotonic()))
            try:
                data = sock.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            buf.extend(data)
            for cmd, direction, payload in extract(buf):
                if direction not in (0x40, 0xe0):
                    continue
                if cmd in (0x07, 0x01) and payload:
                    count = payload[0]
                    for i in range(min(count, (len(payload) - 1)//2)):
                        kind, value = payload[1 + 2*i:3 + 2*i]
                        if kind in COMPONENTS and value & 0x7f <= 100:
                            result['battery'][COMPONENTS[kind]] = {'percent': value & 0x7f, 'charging': bool(value & 0x80)}
                elif cmd in (0x1e, 0x03) and len(payload) >= 2:
                    result['anc'] = MODES.get(payload[1], 'Unknown mode')
                elif cmd == 0x41 and payload:
                    result['latency'] = {1: 'On', 2: 'Off'}.get(payload[0], 'Unknown')
            # Do not hold the Bluetooth socket until the entire timeout if
            # all requested readings have already arrived. This reduces the
            # latency of the next user action sharing this device connection.
            if (result['battery'] and result['anc'] is not None
                    and result['latency'] is not None):
                break
    return result

# Configuration commands are limited to the verified Nothing NT Link operations.
SET_MODES = {'ANC High': 1, 'ANC Medium': 2, 'ANC Low': 3,
             'Adaptive ANC': 4, 'Off': 5, 'Transparency': 7}

def set_frame(command, payload):
    body = struct.pack('<BHHH', 0x55, 0x0160, command | (0xf0 << 8), len(payload)) + b'\x01' + payload
    return body + struct.pack('<H', crc16(body))

def change_setting(address, kind, value, channel=16):
    """Set one supported setting and verify using a fresh GET on the same RFCOMM link."""
    if kind == 'anc':
        if value not in SET_MODES:
            raise ValueError('Unsupported ANC mode')
        command, payload, get_cmd = 0x0f, bytes([1, SET_MODES[value], 0]), 0x1e
    elif kind == 'latency':
        if value not in ('On', 'Off'):
            raise ValueError('Unsupported latency value')
        command, payload, get_cmd = 0x40, bytes([1 if value == 'On' else 2]), 0x41
    else:
        raise ValueError('Setting not implemented')
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
        sock.settimeout(5)
        sock.connect((address, channel))
        # Device-info request activates the NT Link session on some models.
        sock.sendall(frame(0x06))
        buf = bytearray()
        def receive_until(wanted_cmd, wanted_direction, timeout):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                sock.settimeout(max(.1, deadline - time.monotonic()))
                try: data = sock.recv(4096)
                except socket.timeout: return None
                if not data: return None
                buf.extend(data)
                for cmd, direction, response in extract(buf):
                    if cmd == wanted_cmd and direction == wanted_direction:
                        return response
            return None
        if receive_until(0x06, 0x40, 2.0) is None:
            raise RuntimeError('Device-info handshake failed; setting not sent')
        sock.sendall(set_frame(command, payload))
        # An ACK alone is insufficient; read back actual state.
        receive_until(command, 0x70, 1.0)
        sock.sendall(frame(get_cmd))
        response = receive_until(get_cmd, 0x40, 3.0)
        if response is None:
            raise RuntimeError('No read-back response; setting may have changed')
        if kind == 'anc':
            actual = MODES.get(response[1]) if len(response) >= 2 else None
        else:
            actual = {1:'On', 2:'Off'}.get(response[0]) if response else None
        if actual != value:
            raise RuntimeError(f'Expected {value}, device reported {actual or "unknown"}')
        return actual


# Find-earbud commands follow community reverse-engineered NTAPP behavior.
# Do not add arbitrary write operations without device-level testing.
def experimental_command(address, kind, value=None, channel=16):
    if kind == 'find':
        if value not in ('left_on','left_off','right_on','right_off'):
            raise ValueError('Invalid find action')
        side = 2 if value.startswith('left') else 3
        state = 1 if value.endswith('_on') else 0
        command, payload, is_write = 0x02, bytes([side,state]), True
    else:
        raise ValueError('Unsupported command')
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as sock:
        sock.settimeout(4)
        sock.connect((address,channel))
        sock.sendall(frame(0x06))
        buf=bytearray()
        def receive(wanted, timeout):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                sock.settimeout(max(.1,deadline-time.monotonic()))
                try: data=sock.recv(4096)
                except socket.timeout: break
                if not data: break
                buf.extend(data)
                for cmd, direction, response in extract(buf):
                    if cmd==wanted and direction in (0x40,0x70,0xe0):
                        return response
            return None
        if receive(0x06,2) is None:
            raise RuntimeError('NT Link handshake failed')
        sock.sendall(set_frame(command,payload) if is_write else frame(command))
        response=receive(command,2.5)
        return 'Command sent (sound not independently verified)'

def find_for_seconds(address,side,seconds=8):
    if side not in ('left','right'): raise ValueError('Invalid side')
    if not 1<=seconds<=15: raise ValueError('Invalid duration')
    try:
        experimental_command(address,'find',side+'_on')
        time.sleep(seconds)
    finally:
        # Best-effort stop, including if initial start fails.
        experimental_command(address,'find',side+'_off')
    return f'{side.title()} find sound stopped'


# Hardware-tested CMF Buds 2 dual connection protocol.
def dual_operation(address, kind, value=None, channel=16):
    if kind not in ('get','set'):
        raise ValueError('Unsupported operation')
    if kind=='set' and value not in ('On','Off'):
        raise ValueError('Expected On or Off')
    with socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM,socket.BTPROTO_RFCOMM) as sock:
        sock.settimeout(5);sock.connect((address,channel))
        sock.sendall(frame(0x06))
        buf=bytearray()
        def recv(wanted,direction,timeout=2):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                sock.settimeout(max(.1,deadline-time.monotonic()))
                try: chunk=sock.recv(4096)
                except socket.timeout: return None
                if not chunk: return None
                buf.extend(chunk)
                for c,d,payload in extract(buf):
                    if c==wanted and d==direction:return payload
            return None
        if recv(0x06,0x40,2) is None:
            raise RuntimeError('NTAPP handshake failed')
        if kind=='set':
            sock.sendall(set_frame(0x1a,b'\x01' if value=='On' else b'\x00'))
            ack=recv(0x1a,0x70,2)
            if ack is None: raise RuntimeError('Dual setting acknowledgement missing')
        sock.sendall(frame(0x27))
        response=recv(0x27,0x40,3)
        state={0:'Off',1:'On'}.get(response[0],'Unknown') if response else 'Unknown'
        if kind=='set' and state!=value:raise RuntimeError(f'Expected {value}, got {state}')
        return state

def dual_devices(address, channel=16):
    # Proven read-only paginated 0xC028 device list.
    def get_page(sock, offset):
        body=bytes([0x55,0x60,0x01,0x28,0xc0,1,0,1,offset])
        sock.sendall(body+struct.pack('<H',crc16(body)))
        buf=bytearray();out=[];until=time.monotonic()+2.0
        while time.monotonic()<until:
            sock.settimeout(max(.1,until-time.monotonic()))
            try: raw=sock.recv(4096)
            except socket.timeout:break
            if not raw:break
            buf.extend(raw)
            out.extend(payload for cmd,direction,payload in extract(buf) if cmd==0x28 and direction==0x40)
        return out
    devices=[];seen=set()
    with socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM,socket.BTPROTO_RFCOMM) as sock:
        sock.settimeout(5);sock.connect((address,channel))
        for _ in range(10):
            if len(devices)>=20:break
            pages=get_page(sock,len(devices))
            if not pages:break
            added=0
            for payload in pages:
                if len(devices) >= 20:
                    break
                if len(payload)<3:continue
                pos=3
                for _ in range(payload[2]):
                    if len(devices) >= 20 or pos+8>len(payload):break
                    flag=payload[pos];raw_mac=payload[pos+1:pos+7];n=payload[pos+7]&0x7f
                    if pos+8+n>len(payload):break
                    name=payload[pos+8:pos+8+n].decode('utf-8','replace')
                    mac=':'.join(f'{b:02X}' for b in raw_mac)
                    pos+=8+n
                    if mac in seen:continue
                    seen.add(mac);added+=1
                    devices.append({'name':name or mac,'mac':mac,'connected':bool(flag&0x0f),'self':bool(flag&0xf0)})
            if not added:break
    return devices
