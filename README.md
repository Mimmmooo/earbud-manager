# Earbud Manager

A lightweight, unofficial Bluetooth earbuds manager for **Ubuntu GNOME**, built with Python, GTK 4 and libadwaita. Bluetooth controls use Nothing/CMF's NTAPP protocol via BlueZ.

**Version:** `v0.9.3-rc1` · **Tested device:** CMF Buds 2 · **License:** MIT

> This is a community project, not affiliated with Nothing. Windows and macOS versions are not available.

## Features

- **Battery:** left, right and charging case levels where reported. Falls back to a single BlueZ battery reading if none are available.
- **ANC:** noise cancellation modes, Transparency and Off.
- **Gaming mode:** low-latency ON/OFF.
- **Dual Connection:** multipoint ON/OFF, with firmware read-back.
- **Find My Earbuds:** separate left/right sound with manual stop and a 15-second timer. **Do not wear earbuds when ringing.**
- **Remembered Devices:** read-only list from the earbuds.
- **Rename:** edit the device name from the header; also updates its local Ubuntu Bluetooth alias.
- **Multiple connected devices:** select one from the header dropdown. Disconnected devices have no settings cards.

Battery, ANC and Gaming Mode are checked about every 12 seconds; Dual Connection about every 24 seconds; remembered devices about every 60 seconds while the app is open. Actual updates can take longer if Bluetooth is busy. Ultra Bass, Equalizer, Spatial Audio and custom controls still require the Nothing X phone app.

## Install

**Ubuntu 26.04 GNOME** is the primary test target. Pair and connect the earbuds in **Settings → Bluetooth** first.

**Recommended: Debian package.** Download the `.deb` asset from [Releases](https://github.com/Mimmmooo/earbud-manager/releases) for the version you want, then run from the download folder:

```bash
sudo apt install './earbud-manager_0.9.3~rc1-1_all.deb'
```

APT installs required system dependencies if available. No manual Python or pip setup is needed; Internet may be required for dependencies. **Check the release version:** the older `v0.9.1-rc2` asset does not include the latest UI.

**Install from source instead:**

```bash
git clone https://github.com/Mimmmooo/earbud-manager.git
cd earbud-manager
./install.sh
```

Do not mix source and `.deb` installations. For testing a new branch without installing it:

```bash
/usr/bin/python3 src/earbuds_manager.py
```

Launch **Earbud Manager** from Applications or run `earbud-manager`. Uninstall a Debian package with `sudo apt remove earbud-manager`; uninstall source installs with `./uninstall.sh`. Local saved names are preserved.

See [INSTALLATION.md](INSTALLATION.md) for building and publishing a package.

## Limitations and privacy

Only **CMF Buds 2** has been the hardware test target. Some controls and battery components may vary by model or firmware. Remembered devices are **read-only**; switching between them is not implemented. A local rename does not change the earbuds' name on phones or other computers.

The app communicates locally with BlueZ and the earbuds. **No account, cloud service or telemetry is used.** Device names and Bluetooth addresses may appear in local configuration or diagnostic output; redact them before sharing logs or screenshots.

## Contribute and test

```bash
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 -m compileall -q src tests
bash -n install.sh uninstall.sh packaging/build-deb.sh
```

See [protocol notes](docs/PROTOCOL.md), [contribution guide](CONTRIBUTING.md), [security policy](SECURITY.md), and [MIT license](LICENSE).
