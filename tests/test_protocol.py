"""Offline validation of packet encoding. No Bluetooth device is accessed."""
import pathlib
import struct
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from nothing_protocol import crc16, frame, set_frame, extract, SET_MODES


class ProtocolTests(unittest.TestCase):
    def test_get_dual_status_frame(self):
        packet = frame(0x27)
        self.assertEqual(packet[0], 0x55)
        self.assertEqual(packet[3:5], bytes.fromhex('27 c0'))
        self.assertEqual(struct.unpack_from('<H', packet, len(packet) - 2)[0], crc16(packet[:-2]))

    def test_set_dual_on_off(self):
        for value in (0, 1):
            packet = set_frame(0x1a, bytes([value]))
            self.assertEqual(packet[3:5], bytes.fromhex('1a f0'))
            self.assertEqual(packet[8], value)
            self.assertEqual(struct.unpack_from('<H', packet, len(packet) - 2)[0], crc16(packet[:-2]))

    def test_parse_status_response(self):
        for status in (0, 1):
            body = struct.pack('<BHHH', 0x55, 0x0160, 0x4027, 1) + b'\x01' + bytes([status])
            wire = body + struct.pack('<H', crc16(body))
            # Parser is defined for complete framed packets.
            parsed = extract(bytearray(wire))
            self.assertEqual(parsed, [(0x27, 0x40, bytes([status]))])

    def test_mode_options(self):
        self.assertIn('Transparency', SET_MODES)
        self.assertIn('Off', SET_MODES)

    def test_fragmented_packet(self):
        body = struct.pack('<BHHH', 0x55, 0x0160, 0x4027, 1) + b'\\x01' + b'\\x01'
        packet = body + struct.pack('<H', crc16(body))
        buffer = bytearray(packet[:5])
        self.assertEqual(extract(buffer), [])
        buffer.extend(packet[5:])
        self.assertEqual(extract(buffer), [(0x27, 0x40, b'\\x01')])

    def test_crc_corruption_is_rejected(self):
        body = struct.pack('<BHHH', 0x55, 0x0160, 0x4027, 1) + b'\\x01' + b'\\x01'
        packet = bytearray(body + struct.pack('<H', crc16(body)))
        packet[-1] ^= 0xff
        self.assertEqual(extract(packet), [])

    def test_parser_skips_garbage_prefix(self):
        body = struct.pack('<BHHH', 0x55, 0x0160, 0x4027, 1) + b'\\x01' + b'\\x00'
        packet = body + struct.pack('<H', crc16(body))
        self.assertEqual(extract(bytearray(b'garbage' + packet)),
                         [(0x27, 0x40, b'\\x00')])

    def test_invalid_write_operations_never_open_socket(self):
        from nothing_protocol import change_setting, experimental_command, dual_operation
        with self.assertRaises(ValueError):
            change_setting('not-a-device', 'unknown', 'On')
        with self.assertRaises(ValueError):
            change_setting('not-a-device', 'latency', 'invalid')
        with self.assertRaises(ValueError):
            experimental_command('not-a-device', 'find', 'invalid')
        with self.assertRaises(ValueError):
            dual_operation('not-a-device', 'set', 'invalid')



if __name__ == '__main__':
    unittest.main()
