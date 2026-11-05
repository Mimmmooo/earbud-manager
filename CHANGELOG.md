# Changelog

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
