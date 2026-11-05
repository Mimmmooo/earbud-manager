# Changelog

## v0.9.2-rc1 — compact connection status UI

- Displays settings only for connected Bluetooth audio devices with ✓ Connected below the selected name.
- Shows a device-name dropdown only if multiple Bluetooth audio devices are connected; one device's controls are displayed at a time.
- Removes the separate Connection, NTAPP connection, and Last action rows.
- Displays a single BlueZ `Battery` fallback only when no left/right/case component reading is available, hiding the individual battery rows in that case.
- Preserves individual left/right/case battery bars, ANC, gaming, multipoint, Find My Earbuds and header rename.
- Replaces the permanent Last action row with transient notifications for operation failures.
- Drops stale telemetry on disconnect and removes disconnected-device settings from the page.
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
