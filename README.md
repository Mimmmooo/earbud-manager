# Earbud Manager

**Linux, Windows, and macOS editions are planned. The Ubuntu/GNOME edition is the only currently runnable and hardware-tested variant.**

An **unofficial, community-built GNOME configuration app** for Bluetooth earbuds on Linux. The currently tested device family is **CMF Buds 2**, using Nothing/CMF's proprietary NTAPP protocol over Bluetooth RFCOMM.

> **Release status:** public hardware-testing build, **v0.9.1-rc2**. This is not a Nothing/CMF product and is not endorsed by Nothing Technology Limited. Test new versions before depending on them.

## Features

| Feature | Status |
| --- | --- |
| Original GNOME Adwaita settings/list interface | Included |
| Left / right / case battery readings | Displayed **when reported** by firmware |
| Battery summary in the app | Lower of available left/right readings; BlueZ fallback |
| ANC / Transparency / Off | Device commands with read-back verification |
| Low Latency / Gaming mode | ON/OFF switch with read-back verification |
| Dual Connection / Multipoint | ON/OFF switch with read-back verification on CMF Buds 2 |
| Find My Earbuds | Separate left/right sound, toggle to stop, 15-second circular timer |
| Remembered devices | Read-only paired device list and status |
| Local rename | Per Bluetooth device, **only on this PC** |
| Ultra Bass / Equalizer / Spatial Audio / Controls | Clearly marked **Use Nothing X app on phone** at bottom |
| Device switching via paired-device list | **Not enabled:** hardware verification still required |
| Custom GNOME Settings Power panel | **Not included**; system Settings are unchanged |

The same application can show connected standard Bluetooth audio devices, though CMF-specific controls require successful device identification and NTAPP support.

## Faster refresh in v0.9.1-rc2

Earlier development builds rebuilt the entire GTK page whenever new battery or setting data arrived. That made toggles appear slow, could reset scroll position, and delayed actions behind background device reads. This release:

- Updates existing GTK rows and progress bars **in place**, without rebuilding the page for changing battery/status values.
- Scans BlueZ on a background worker, keeping GTK responsive while Bluetooth discovery runs.
- Uses separate pools for **user actions**, **battery/status reads**, and **device discovery**.
- Serializes NTAPP operations for each Bluetooth device to avoid overlapping RFCOMM sessions.
- Uses an optimistic switch update while the device command is running, followed by **actual read-back verification**. If verification fails, the app shows an error and refreshes the state.
- Reduces unnecessary telemetry waiting when all expected readings have arrived. Background sampling is limited to about once every 12 seconds while the app is open.

A visual switch responding immediately **does not guarantee** the earbuds finished updating immediately. Bluetooth connection establishment and firmware acknowledgement still take time. No claim is made about a specific latency without measurements on hardware.

## Recommended install: Ubuntu `.deb` package

Download the `.deb` file from the GitHub release and install it through your system package manager. APT automatically fetches missing system dependencies when available. **No manual Python/pip setup is needed.** An internet connection may be required for OS packages. There is no Windows/macOS executable yet. See [INSTALLATION.md](INSTALLATION.md) for exact steps.

## Install on Ubuntu GNOME

Test target: Ubuntu 26.04 with GTK 4, libadwaita, Python 3, BlueZ.

1. Pair and connect your earbuds in **Settings → Bluetooth**.
2. Download and extract the release ZIP (or clone the GitHub repository).
3. Open a terminal in the project directory and run:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer asks before running `sudo`, then uses apt to install required packages and copies the app to system directories:

| Destination | Role |
| --- | --- |
| `/opt/earbud-manager/src/` | Application and protocol implementation |
| `/usr/local/bin/earbud-manager` | Terminal launcher |
| `/usr/local/share/applications/io.github.earbudmanager.App.desktop` | Applications menu shortcut |
| `~/.config/earbuds-manager/local-names.json` | Local names, created on first save; permissions `0600` |

**Downloads can be deleted once installation succeeds.** The executable does not depend on the extracted folder. The app does not change GNOME Settings, create a persistent Bluetooth daemon, or configure autostart.

Launch via Applications → **Earbud Manager**, or:

```bash
earbud-manager
```

For a no-install trial:

```bash
sudo apt install python3 python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-4.0 gir1.2-adw-1 bluez
/usr/bin/python3 src/earbuds_manager.py
```

Do **not** run the GUI with `sudo`. Run as your own logged-in desktop user.

### Update / uninstall

To update, download/extract the newer release and rerun `./install.sh`. The installer replaces installed **application files**, not user-local names. To uninstall, run `./uninstall.sh` from a downloaded/extracted copy of the repository. Local saved names remain unless you delete them manually.

## Everyday usage

- Open the app with earbuds connected. It will populate the battery and control fields asynchronously.
- Change ANC or Low Lag directly with the built-in controls. Switches react immediately, then the application verifies the change over Bluetooth.
- Switch Dual Connection ON/OFF if supported. Turning it OFF can disconnect a different source (for example, a phone); that device may need manual reconnection afterward.
- Find My Earbuds sends sound commands for the selected left or right side. Do not wear earbuds when using this feature.
- Under **Device Settings**, set a custom name. The change stays on this Linux machine only.
- Select **Refresh** under remembered devices to read the list from firmware. Device connection switching is intentionally not offered.

## Privacy & safety

No account login or telemetry backend is used. The application talks locally to BlueZ and the connected earbuds. Device addresses and remembered-device names can occur **in memory and in the local name configuration file**, but no such values are shipped in this repository. **Do not upload terminal logs, screenshots, or `~/.config/earbuds-manager/local-names.json` to public GitHub issues without removing personal identifiers.**

This repository deliberately contains no developer's Bluetooth addresses, usernames, paired-device names, diagnostic captures, or personal directories.

## Known limitations

- **Device-specific:** Some earbuds/firmware versions may not support the current NTAPP commands. Battery components may be absent; case readings may be stale or unavailable when the case is closed or out of range.
- **Timing:** The Bluetooth connection/session and read-back can still take seconds. Optimistic UI is not a claim of instant hardware execution.
- **Multipoint:** Opening an NTAPP session may affect connection state. After disabling Dual Connection, the other source may disconnect.
- **GNOME battery panel:** The app cannot replace GNOME Power settings rows or inject per-bud bars into GNOME Settings. This release makes **no OS-level modifications**.
- **Device switching:** Read-only device list; no connect/disconnect operation exposed until testing confirms behavior.
- **Local names:** Rename is applied in this app only, not the BlueZ alias shown everywhere in Ubuntu.
- **Find My Earbuds:** Firmware-specific commands. Leave earbuds out of ears and use in a safe environment.

## Troubleshooting

**Application not in menu:** Log out/in, or run `earbud-manager` directly. Check the `.desktop` file in `/usr/local/share/applications/`.

**No earbuds found:** Confirm they show Connected in GNOME Bluetooth settings, Bluetooth service is running, and an audio profile is present. The app does not pair devices for you.

**Setting shows an error:** Disconnect/reconnect earbuds, then retry. Another phone may be occupying the proprietary NTAPP connection. Errors are shown in the app and state is re-read.

**Python GI or cairo error:** Install the packages in the no-install command above. Use Ubuntu's `/usr/bin/python3`, not a virtualenv Python missing system GI libraries.

## Development

```bash
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q src tests
bash -n install.sh uninstall.sh
```

The test suite is offline and never sends Bluetooth commands. Protocol details and limitations are in [`docs/PROTOCOL.md`](docs/PROTOCOL.md). New device models should be enabled only after read/write operations have been validated on hardware.

## Contributions and license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [LICENSE](LICENSE). Licensed under MIT.

## Platform editions and shared roadmap

The repository is organized for independent platform integrations. **Do not run the Ubuntu GTK app on Windows or macOS**: it depends on BlueZ, GNOME, and Linux D-Bus. The `platforms/windows` and `platforms/macos` directories document planned ports, not runnable apps.

The long-term goal is consistent battery, ANC, low-latency, multipoint, and local naming features where supported by hardware, using platform-specific Bluetooth adapters and native UI. Platform support will be marked available only after device testing.

The Ubuntu program is installed as **Earbud Manager** via `earbud-manager`. Existing user names under `~/.config/earbuds-manager/` are preserved from previous releases.
