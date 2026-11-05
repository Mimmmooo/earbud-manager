#!/usr/bin/env python3
"""GNOME/Adwaita earbud manager. Device I/O never runs on the GTK thread."""
import concurrent.futures
import json
import math
import os
import re
import threading
import time
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from nothing_protocol import query, change_setting, SET_MODES, experimental_command, dual_operation, dual_devices

BLUEZ = 'org.bluez'
AUDIO_UUIDS = ('0000110b-', '00001108-', '0000111e-', '0000110e-', '0000110d-')
NOTHING_UUID = 'aeac4a03-'
PHONE_ONLY = ('Ultra Bass', 'Equalizer', 'Spatial Audio', 'Controls')
NAME_FILE = Path.home() / '.config' / 'earbuds-manager' / 'local-names.json'


def safe_error(error):
    """Keep Bluetooth device addresses out of user-visible diagnostic text."""
    return re.sub(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', '[Bluetooth device]', str(error))


def unpack(v):
    if isinstance(v, GLib.Variant):
        return unpack(v.unpack())
    if isinstance(v, dict):
        return {k: unpack(item) for k, item in v.items()}
    if isinstance(v, (list, tuple)):
        return [unpack(item) for item in v]
    return v


def known_cmf(device):
    # BlueZ Alias is user-editable; use the original device name for detection.
    return (any(NOTHING_UUID in uuid for uuid in device['uuids'])
            or 'cmf buds 2' in (device.get('original_name') or device['name']).lower())


def validate_device_name(name):
    name = name.strip()
    if not name or len(name) > 64 or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise ValueError('Use 1–64 characters without line breaks or control characters')
    return name


def battery_summary(battery, fallback):
    values = [battery[side]['percent'] for side in ('left', 'right') if battery.get(side)]
    if values:
        return f'{min(values)}% (lowest earbud)'
    return f'{fallback}%' if isinstance(fallback, (int, float)) else 'Not reported'


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.earbudmanager.App')
        self.window = None
        self.bus = None
        # Separate pending/background work from user actions. One active RFCOMM
        # operation per device is enforced by the per-device lock below.
        self.io_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix='earbuds-action')
        self.read_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='earbuds-read')
        self.discovery_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='earbuds-bluez')
        self.io_locks = {}
        self.devices_cache = []
        self.discovery_pending = False
        self.last_discovery = 0.0
        self.last_read = {}
        self.read_pending = set()
        self.busy = set()
        self.cache = {}
        self.dual_cache = {}
        self.messages = {}
        self.remembered = {}
        self.device_fetching = set()
        self.ringing = {}
        self.widgets = {}
        self.groups = []
        self.topology = None
        self._updating = False
        self._device_generation = {}
        self._closing = False
        self.renaming = set()
        try:
            content = json.loads(NAME_FILE.read_text(encoding='utf-8'))
            self.local_names = content if isinstance(content, dict) else {}
        except (ValueError, OSError):
            self.local_names = {}

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.window = Adw.ApplicationWindow(application=self, title='Earbud Manager')
        self.window.set_default_size(600, 690)
        self.page = Adw.PreferencesPage(title='Earbuds', icon_name='audio-headphones-symbolic')
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        toolbar.set_content(self.page)
        self.window.set_content(toolbar)
        self.render_structure([])
        self.discover(force=True)
        GLib.timeout_add_seconds(3, self.periodic)
        self.window.present()

    def periodic(self):
        if self._closing:
            return GLib.SOURCE_REMOVE
        self.discover()
        for device in list(self.devices_cache):
            if known_cmf(device):
                self.schedule_read(device['address'])
        return GLib.SOURCE_CONTINUE

    def device_lock(self, address):
        if address not in self.io_locks:
            self.io_locks[address] = threading.Lock()
        return self.io_locks[address]

    def execute(self, address, func, *args):
        with self.device_lock(address):
            return func(address, *args)

    def bluez_devices(self):
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        response = bus.call_sync(BLUEZ, '/', 'org.freedesktop.DBus.ObjectManager',
                                 'GetManagedObjects', None,
                                 GLib.VariantType('(a{oa{sa{sv}}})'),
                                 Gio.DBusCallFlags.NONE, 3500, None)
        found = []
        for object_path, interfaces in unpack(response)[0].items():
            props = interfaces.get('org.bluez.Device1')
            if not props or not props.get('Connected'):
                continue
            uuids = [str(u).lower() for u in props.get('UUIDs', [])]
            if not any(u.startswith(AUDIO_UUIDS) for u in uuids):
                continue
            found.append({'name': props.get('Alias') or props.get('Name') or 'Bluetooth Audio',
                          'original_name': props.get('Name') or '',
                          'object_path': object_path,
                          'address': props.get('Address', ''),
                          'battery': interfaces.get('org.bluez.Battery1', {}).get('Percentage'),
                          'uuids': uuids})
        return sorted(found, key=lambda x: x['address'])

    def discover(self, force=False):
        if self._closing:
            return
        now = time.monotonic()
        if self.discovery_pending or (not force and now-self.last_discovery < 4):
            return
        self.last_discovery = now
        self.discovery_pending = True
        future = self.discovery_pool.submit(self.bluez_devices)
        def complete(f):
            def ui():
                self.discovery_pending = False
                try:
                    devices = f.result()
                except Exception as e:
                    self.show_error(f'Bluetooth discovery: {safe_error(e)}')
                    return GLib.SOURCE_REMOVE
                old = self.devices_cache
                previous_addresses = {d['address'] for d in old}
                current_addresses = {d['address'] for d in devices}
                for missing in previous_addresses - current_addresses:
                    self._device_generation[missing] = self._device_generation.get(missing, 0) + 1
                    self.cache.pop(missing, None)
                    self.dual_cache.pop(missing, None)
                    self.remembered.pop(missing, None)
                    self.messages.pop(missing, None)
                    self.last_read.pop(missing, None)
                self.devices_cache = devices
                identity = tuple((d['address'], known_cmf(d)) for d in devices)
                if identity != self.topology:
                    self.render_structure(devices)
                else:
                    for dev in devices:
                        self.paint(dev['address'])
                for dev in devices:
                    if known_cmf(dev):
                        self.schedule_read(dev['address'], force=not bool(old))
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        future.add_done_callback(complete)

    def show_error(self, message):
        # Errors never contain personal telemetry in logs or project files.
        for device in self.devices_cache:
            self.messages[device['address']] = message
            self.paint(device['address'])

    def schedule_read(self, address, force=False):
        if self._closing:
            return
        if address in self.read_pending or address in self.busy:
            return
        now = time.monotonic()
        if not force and now-self.last_read.get(address, 0) < 12:
            return
        self.last_read[address] = now
        self.read_pending.add(address)
        generation = self._device_generation.get(address, 0)
        fut = self.read_pool.submit(self.execute, address, query)
        def complete(f):
            def ui():
                self.read_pending.discard(address)
                if generation != self._device_generation.get(address, 0):
                    return GLib.SOURCE_REMOVE
                try:
                    self.cache[address] = f.result()
                except Exception as e:
                    self.messages[address] = 'Reading failed: ' + safe_error(e)
                self.paint(address)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        fut.add_done_callback(complete)

    def control(self, address, kind, value=None):
        if self._closing or address in self.busy:
            return
        self.busy.add(address)
        self._device_generation[address] = self._device_generation.get(address, 0)+1
        self.messages[address] = f'Applying {kind}…'
        previous = (self.dual_cache.get(address) if kind == 'dual_set'
                    else self.cache.get(address, {}).get(kind))
        # Optimistic switch display; final state comes from device verification.
        if kind == 'latency':
            self.cache.setdefault(address, {})['latency'] = value
        elif kind == 'dual_set':
            self.dual_cache[address] = value
        elif kind == 'anc':
            self.cache.setdefault(address, {})['anc'] = value
        self.paint(address)
        if kind in ('anc', 'latency'):
            job = self.io_pool.submit(self.execute, address, change_setting, kind, value)
        elif kind == 'dual_set':
            job = self.io_pool.submit(self.execute, address, dual_operation, 'set', value)
        elif kind == 'dual_get':
            job = self.io_pool.submit(self.execute, address, dual_operation, 'get')
        else:
            raise ValueError('Unknown control')

        def complete(f):
            def ui():
                self.busy.discard(address)
                try:
                    result = f.result()
                    if kind.startswith('dual_'):
                        self.dual_cache[address] = result
                    else:
                        self.cache.setdefault(address, {})[kind] = result
                    self.messages[address] = f'{kind}: {result} (verified)'
                except Exception as e:
                    self.messages[address] = f'{kind}: {safe_error(e)}'
                    if kind == 'dual_set':
                        self.dual_cache[address] = previous
                    elif kind in ('anc', 'latency'):
                        self.cache.setdefault(address, {})[kind] = previous
                self.paint(address)
                # Refresh hardware state after completion (do not start concurrent
                # reads while the user command is still executing).
                self.last_read[address] = 0
                self.schedule_read(address, force=True)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        job.add_done_callback(complete)

    def read_dual(self, address):
        if address in self.busy or address in self.dual_cache:
            return
        self.control(address, 'dual_get')

    def read_remembered(self, address):
        if self._closing:
            return
        if address in self.device_fetching or address in self.busy:
            return
        self.device_fetching.add(address)
        fut = self.read_pool.submit(self.execute, address, dual_devices)
        def complete(f):
            def ui():
                self.device_fetching.discard(address)
                try:
                    self.remembered[address] = f.result()
                    self.populate_remembered(address)
                except Exception as e:
                    self.messages[address] = f'Device list: {safe_error(e)}'
                self.paint(address)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        fut.add_done_callback(complete)

    def set_bluez_alias(self, object_path, name):
        """Set this computer's BlueZ alias, not the earbuds' global name."""
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        bus.call_sync(BLUEZ, object_path, 'org.freedesktop.DBus.Properties',
                      'Set', GLib.Variant('(ssv)', ('org.bluez.Device1', 'Alias',
                                                    GLib.Variant('s', name))),
                      None, Gio.DBusCallFlags.NONE, 5000, None)
        result = bus.call_sync(BLUEZ, object_path, 'org.freedesktop.DBus.Properties',
                               'Get', GLib.Variant('(ss)', ('org.bluez.Device1', 'Alias')),
                               GLib.VariantType('(v)'), Gio.DBusCallFlags.NONE, 5000, None)
        actual = unpack(result)[0]
        if actual != name:
            raise RuntimeError('Bluetooth alias verification failed')

    def save_local_name(self, address, name):
        """Persist the display name only after the OS-level rename succeeds."""
        names = dict(self.local_names)
        names[address] = name
        NAME_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = NAME_FILE.with_suffix('.tmp')
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(names, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, NAME_FILE)
            NAME_FILE.chmod(0o600)
        finally:
            if tmp.exists():
                tmp.unlink()
        self.local_names = names

    def rename_dialog(self, address):
        dev = next((d for d in self.devices_cache if d['address'] == address), None)
        if not dev or address in self.renaming:
            return
        dialog = Gtk.Dialog(title='Rename Bluetooth device', transient_for=self.window,
                            modal=True)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Save', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_spacing(10)
        label = Gtk.Label(label='This name also appears in Ubuntu Bluetooth Settings.',
                          xalign=0, wrap=True)
        box.append(label)
        entry = Gtk.Entry(text=self.local_names.get(address, dev['name']))
        entry.set_max_length(64)
        entry.set_activates_default(True)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box.append(entry)

        def response(_dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                try:
                    name = validate_device_name(entry.get_text())
                except ValueError as error:
                    self.show_rename_error(str(error))
                else:
                    self.rename_device(address, dev['object_path'], name)
            dialog.destroy()
        dialog.connect('response', response)
        dialog.present()
        entry.grab_focus()

    def show_rename_error(self, message):
        dialog = Adw.MessageDialog.new(self.window, 'Unable to rename device', message)
        dialog.add_response('ok', 'OK')
        dialog.present()

    def rename_device(self, address, object_path, name):
        if address in self.renaming:
            return
        self.renaming.add(address)
        button = self.widgets.get(address, {}).get('rename_button')
        if button:
            button.set_sensitive(False)
        # D-Bus calls run away from GTK; no RFCOMM command is involved.
        future = self.discovery_pool.submit(self.set_bluez_alias, object_path, name)

        def complete(f):
            def ui():
                self.renaming.discard(address)
                current_button = self.widgets.get(address, {}).get('rename_button')
                if current_button:
                    current_button.set_sensitive(True)
                try:
                    f.result()
                except Exception as error:
                    self.show_rename_error(safe_error(error))
                    return GLib.SOURCE_REMOVE
                # BlueZ has applied the new alias even if the optional legacy
                # local-name cache cannot be written.
                for device in self.devices_cache:
                    if device['address'] == address:
                        device['name'] = name
                group = self.widgets.get(address, {}).get('main_group')
                if group:
                    group.set_title(name)
                try:
                    self.save_local_name(address, name)
                except OSError as error:
                    self.show_rename_error(
                        'Bluetooth Settings was renamed, but local name backup failed: '
                        + safe_error(error))
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        future.add_done_callback(complete)

    def add_group(self, group):
        self.page.add(group)
        self.groups.append(group)
        return group

    def add_battery_row(self, group, title):
        row = Adw.ActionRow(title=title, subtitle='Reading…')
        bar = Gtk.ProgressBar(valign=Gtk.Align.CENTER)
        bar.set_size_request(125, -1)
        row.add_suffix(bar)
        group.add(row)
        return row, bar

    def render_structure(self, devices):
        self.topology = tuple((d['address'], known_cmf(d)) for d in devices)
        for group in self.groups:
            self.page.remove(group)
        self.groups.clear()
        self.widgets.clear()
        if not devices:
            g = self.add_group(Adw.PreferencesGroup(title='No connected earbuds'))
            g.add(Adw.ActionRow(title='Connect Bluetooth earbuds to get started',
                                subtitle='Waiting for a device'))
            return
        for dev in devices:
            address = dev['address']
            cmf = known_cmf(dev)
            refs = self.widgets[address] = {}
            g = self.add_group(Adw.PreferencesGroup(
                title=self.local_names.get(address, dev['name']),
                description='Bluetooth audio device'))
            refs['main_group'] = g
            edit_button = Gtk.Button(icon_name='document-edit-symbolic',
                                     valign=Gtk.Align.CENTER)
            edit_button.add_css_class('flat')
            edit_button.set_tooltip_text('Rename in Earbud Manager and Ubuntu Bluetooth Settings')
            edit_button.set_opacity(0.0)
            edit_button.connect('clicked', lambda _btn, a=address: self.rename_dialog(a))
            g.set_header_suffix(edit_button)
            refs['rename_button'] = edit_button
            hover = Gtk.EventControllerMotion()
            hover.connect('enter', lambda *_args, btn=edit_button: btn.set_opacity(1.0))
            hover.connect('leave', lambda *_args, btn=edit_button: btn.set_opacity(0.0))
            g.add_controller(hover)
            g.add(Adw.ActionRow(title='Connection', subtitle='Connected'))
            summary = Adw.ActionRow(title='Bluetooth battery', subtitle='Reading…')
            g.add(summary)
            refs['summary'] = summary
            if not cmf:
                g.add(Adw.ActionRow(title='Individual batteries',
                                    subtitle='Device-specific protocol not available'))
                continue
            for side, label in (('left', 'Left earbud'), ('right', 'Right earbud'),
                                ('case', 'Charging case')):
                refs[side] = self.add_battery_row(g, label)
            refs['status'] = Adw.ActionRow(title='NTAPP connection', subtitle='Reading…')
            g.add(refs['status'])
            choices = list(SET_MODES)
            anc = Adw.ComboRow(title='ANC / Transparency', subtitle='Select a mode to apply')
            anc.set_model(Gtk.StringList.new(choices))
            anc.set_sensitive(False)
            anc.connect('notify::selected', self.on_anc, address, choices)
            g.add(anc)
            refs['anc'] = anc
            latency = Adw.SwitchRow(title='Low latency / Gaming mode')
            latency.set_sensitive(False)
            latency.connect('notify::active', self.on_switch, address, 'latency')
            g.add(latency)
            refs['latency'] = latency
            refs['message'] = Adw.ActionRow(title='Last action', subtitle='Ready')
            g.add(refs['message'])

            dual_group = self.add_group(Adw.PreferencesGroup(title='Dual Connection',
                                                description='Multipoint ON/OFF'))
            status = Adw.ActionRow(title='Device state', subtitle='Unknown')
            refresh = Gtk.Button(label='Refresh status', valign=Gtk.Align.CENTER)
            refresh.connect('clicked', lambda _button, a=address: self.control(a, 'dual_get'))
            status.add_suffix(refresh)
            dual_group.add(status)
            refs['dual_status'] = status
            refs['dual_refresh'] = refresh
            dual = Adw.SwitchRow(title='Dual Connection')
            dual.set_sensitive(False)
            dual.connect('notify::active', self.on_switch, address, 'dual_set')
            dual_group.add(dual)
            refs['dual'] = dual

            ring_group = self.add_group(Adw.PreferencesGroup(
                title='Find My Earbuds',
                description='Keep earbuds out of your ears. Tap to play or stop. Stops after 15 seconds.'))
            for side in ('left', 'right'):
                key = (address, side)
                row = Adw.ActionRow(title=f'{side.title()} earbud')
                overlay = Gtk.Overlay(valign=Gtk.Align.CENTER)
                overlay.set_size_request(54, 54)
                circle = Gtk.DrawingArea()
                circle.set_content_width(54)
                circle.set_content_height(54)
                circle.set_draw_func(lambda _area, cr, w, h, k=key: self.draw_ring(cr, w, h, k))
                overlay.set_child(circle)
                btn = Gtk.Button(icon_name='media-playback-start-symbolic',
                                 valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
                btn.add_css_class('circular')
                btn.connect('clicked', lambda _btn, a=address, s=side: self.ring_action(a, s))
                overlay.add_overlay(btn)
                row.add_suffix(overlay)
                ring_group.add(row)
                refs[f'ring_{side}'] = (btn, circle)

            settings = self.add_group(Adw.PreferencesGroup(title='Device Settings',
                                        description='Remembered devices'))
            heading = Adw.ActionRow(title='Remembered devices',
                                    subtitle='Read-only; switching not hardware-tested')
            refresh = Gtk.Button(label='Refresh', valign=Gtk.Align.CENTER)
            refresh.connect('clicked', lambda _btn, a=address: self.read_remembered(a))
            heading.add_suffix(refresh)
            settings.add(heading)
            refs['remembered_group'] = settings
            refs['remembered_header'] = heading
            refs['remembered_rows'] = []
            self.populate_remembered(address)

            phone = self.add_group(Adw.PreferencesGroup(
                title='Configuration capabilities',
                description='Features requiring the phone app are kept below supported controls.'))
            for feature in PHONE_ONLY:
                row = Adw.ActionRow(title=feature, subtitle='Use Nothing X app on phone')
                row.set_sensitive(False)
                phone.add(row)
            self.paint(address)
            self.read_dual(address)

    def populate_remembered(self, address):
        refs = self.widgets.get(address)
        if not refs or 'remembered_group' not in refs:
            return
        group = refs['remembered_group']
        for row in refs['remembered_rows']:
            group.remove(row)
        refs['remembered_rows'].clear()
        devices = self.remembered.get(address)
        if devices is None:
            devices = [{'name': 'Press Refresh to read', 'connected': False, 'self': False}]
        if not devices:
            devices = [{'name': 'No remembered devices reported', 'connected': False, 'self': False}]
        for dev in devices:
            subtitle = ('Connected' if dev['connected'] else 'Disconnected')
            if dev['self']:
                subtitle += ' · This computer'
            row = Adw.ActionRow(title=dev['name'], subtitle=subtitle)
            group.add(row)
            refs['remembered_rows'].append(row)

    def on_anc(self, widget, _param, address, choices):
        if self._updating or address in self.busy:
            return
        index = widget.get_selected()
        if index >= len(choices):
            return
        selected = choices[index]
        if selected != self.cache.get(address, {}).get('anc'):
            self.control(address, 'anc', selected)

    def on_switch(self, widget, _param, address, kind):
        if self._updating or address in self.busy:
            return
        selected = 'On' if widget.get_active() else 'Off'
        actual = (self.dual_cache.get(address) if kind == 'dual_set'
                  else self.cache.get(address, {}).get('latency'))
        if selected != actual:
            self.control(address, kind, selected)

    def paint(self, address):
        refs = self.widgets.get(address)
        if not refs or 'main_group' not in refs or 'status' not in refs:
            return
        dev = next((d for d in self.devices_cache if d['address'] == address), None)
        if not dev:
            return
        data = self.cache.get(address, {})
        battery = data.get('battery', {})
        refs['summary'].set_subtitle(battery_summary(battery, dev.get('battery')))
        for side in ('left', 'right', 'case'):
            row, bar = refs[side]
            val = battery.get(side)
            row.set_subtitle((f"{val['percent']}%" + (' · Charging' if val['charging'] else ''))
                             if val is not None else 'Not reported')
            bar.set_visible(val is not None)
            if val is not None:
                bar.set_fraction(max(0.0, min(1.0, val['percent']/100)))
        refs['status'].set_subtitle('Connected' if data else 'Reading device…')
        refs['message'].set_subtitle(self.messages.get(address, 'Ready'))
        busy = address in self.busy
        self._updating = True
        try:
            anc = data.get('anc')
            if anc in SET_MODES:
                refs['anc'].set_selected(list(SET_MODES).index(anc))
            refs['anc'].set_sensitive(anc in SET_MODES and not busy)
            latency = data.get('latency')
            refs['latency'].set_active(latency == 'On')
            refs['latency'].set_sensitive(latency in ('On', 'Off') and not busy)
            dual = self.dual_cache.get(address)
            refs['dual_status'].set_subtitle(dual or 'Unknown')
            refs['dual'].set_active(dual == 'On')
            refs['dual'].set_sensitive(dual in ('On', 'Off') and not busy)
            refs['dual_refresh'].set_sensitive(not busy)
        finally:
            self._updating = False

    def ring_action(self, address, side):
        if self._closing:
            return
        key = (address, side)
        existing = self.ringing.get(key)
        if existing:
            self.stop_ring(address, side, existing['token'])
            return
        token = object()
        self.ringing[key] = {'token': token, 'start': None, 'start_future': None}
        self.messages[address] = f'Find My Earbuds: starting {side}…'
        self.paint(address)
        self.update_ring(key)
        fut = self.io_pool.submit(self.execute, address, experimental_command, 'find', side+'_on')
        def done(f):
            def ui():
                if self.ringing.get(key, {}).get('token') is not token:
                    return GLib.SOURCE_REMOVE
                try:
                    f.result()
                    self.ringing[key]['start'] = time.monotonic()
                    GLib.timeout_add(100, self.tick_ring, address, side, token)
                    self.messages[address] = f'Find My Earbuds: {side} playing'
                except Exception as e:
                    self.messages[address] = f'Find My Earbuds: {safe_error(e)}'
                    self.stop_ring(address, side, token)
                self.paint(address)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        self.ringing[key]['start_future'] = fut
        fut.add_done_callback(done)

    def stop_ring(self, address, side, token):
        key = (address, side)
        if self.ringing.get(key, {}).get('token') is not token:
            return
        active = self.ringing.pop(key)
        self.update_ring(key)
        self.messages[address] = f'Find My Earbuds: stopping {side}…'
        self.paint(address)
        def done(f):
            def ui():
                try:
                    f.result()
                    self.messages[address] = f'Find My Earbuds: {side} stopped'
                except Exception as e:
                    self.messages[address] = f'Stop command failed: {safe_error(e)}'
                self.paint(address)
                return GLib.SOURCE_REMOVE
            GLib.idle_add(ui)
        def send_stop(_finished=None):
            # If Play is still in flight, enqueue Stop only after it finishes.
            fut = self.io_pool.submit(self.execute, address, experimental_command,
                                      'find', side + '_off')
            fut.add_done_callback(done)

        start_future = active.get('start_future')
        if start_future is not None and not start_future.done():
            start_future.add_done_callback(send_stop)
        else:
            send_stop()

    def tick_ring(self, address, side, token):
        key = (address, side)
        item = self.ringing.get(key)
        if not item or item['token'] is not token:
            return GLib.SOURCE_REMOVE
        if item['start'] is None:
            return GLib.SOURCE_REMOVE
        if time.monotonic()-item['start'] >= 15:
            self.stop_ring(address, side, token)
            return GLib.SOURCE_REMOVE
        self.update_ring(key)
        return GLib.SOURCE_CONTINUE

    def update_ring(self, key):
        refs = self.widgets.get(key[0], {})
        widget = refs.get('ring_'+key[1])
        if not widget:
            return
        button, circle = widget
        active = key in self.ringing
        button.set_icon_name('media-playback-stop-symbolic' if active else 'media-playback-start-symbolic')
        button.set_tooltip_text('Stop sound' if active else 'Play sound (up to 15 seconds)')
        circle.queue_draw()

    def draw_ring(self, cr, width, height, key):
        state = self.ringing.get(key)
        fraction = (min(1.0, (time.monotonic()-state['start'])/15)
                    if state and state['start'] is not None else 0)
        x, y = width/2, height/2
        radius = min(width, height)/2 - 3
        cr.set_line_width(3.5)
        cr.set_source_rgba(.5, .5, .5, .25)
        cr.arc(x, y, radius, 0, 2*math.pi)
        cr.stroke()
        if state:
            cr.set_source_rgba(.22, .63, .95, 1)
            cr.arc(x, y, radius, -math.pi/2, -math.pi/2 + 2*math.pi*fraction)
            cr.stroke()

    def do_shutdown(self):
        # Best effort: stop any active find tones before the process exits.
        # Complete pending Play first, otherwise a late Play may outlive Stop.
        self._closing = True
        active = list(self.ringing.items())
        self.ringing.clear()
        for (address, side), item in active:
            start_future = item.get('start_future')
            try:
                if start_future is not None:
                    start_future.result(timeout=12)
            except Exception:
                pass
            try:
                self.execute(address, experimental_command, 'find', side + '_off')
            except Exception:
                pass  # Bluetooth may already be disconnected.
        super().do_shutdown()


if __name__ == '__main__':
    App().run(None)
