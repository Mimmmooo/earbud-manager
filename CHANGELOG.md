# Changelog

## v0.9.2-rc1 — compact connection status UI

- Shows ✓ Connected or ✕ Disconnected directly below each paired Bluetooth audio device's name.
- Displays paired/disconnected Bluetooth audio devices with device-specific controls disabled until connected.
- Removes the separate Connection, Bluetooth battery summary, NTAPP connection, and Last action rows.
- Preserves individual left/right/case battery bars, ANC, gaming, multipoint, Find My Earbuds and header rename.
- Replaces the permanent Last action row with transient notifications for operation failures.
- Drops stale telemetry when a connected device disconnects, while keeping the paired device visible.
- This is source-code release-candidate metadata; a new v0.9.2-rc1 .deb is not yet published.


## v0.9.1-rc2 — public test build

- Retains the originally approved GNOME Adwaita list UI and Find My Earbuds circular controls.
- Keeps unsupported phone-only features at the bottom.
- Updates battery/status/switch widgets in place to avoid costly page rebuilds and scroll jumps.
- Moves BlueZ discovery off the GTK main thread.
- Separates user actions from telemetry worker queues, serializing requests per device.
- Shows optimistic switch state immediately, with firmware read-back validation afterward.
- Returns telemetry reads earlier when sufficient readings have arrived.
- Provides permanent `/opt` installation, launcher, uninstall, and privacy-safe GitHub documentation.

### Still not implemented

- Direct paired-device switching (requires hardware tests).
- Custom GNOME Settings/Power panel integration (out of scope).
