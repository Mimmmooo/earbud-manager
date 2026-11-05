# Install Earbud Manager

## Ubuntu / Debian (recommended)

**Version note:** This command installs the previously published **v0.9.1-rc2** package. The current source version is **v0.9.3-rc1**; a matching `.deb` has not yet been published. To try the new interface without replacing an existing installation, run `/usr/bin/python3 src/earbuds_manager.py` from the updated source checkout.

Download the `.deb` release asset and open it with your system package installer. Alternatively, from its download directory:

```bash
sudo apt install ./earbud-manager_0.9.1.rc2-1_all.deb
```

APT installs required **OS packages automatically**, if they are absent. An internet connection and administrator authentication may be required. The program then appears as **Earbud Manager** in Applications. The package does not patch GNOME Settings.

Uninstall:

```bash
sudo apt remove earbud-manager
```

Personal local naming data in `~/.config/earbuds-manager/` is retained unless removed manually.

## Source code (Ubuntu)

```bash
git clone https://github.com/Mimmmooo/earbud-manager.git
cd earbud-manager
./install.sh
```

This also installs Ubuntu's Python/GTK/BlueZ packages using APT. For a trial without system installation, see README.md.

**Choose one installation method.** Do not mix the packaged `.deb` installation with the source installer. Source install and uninstall scripts refuse to run if the `earbud-manager` Debian package is installed, preventing accidental deletion of package-owned files.

## Windows and macOS

**Not available yet.** No `.exe`, `.msi`, `.dmg` or `.pkg` build currently exists. Do not advertise these operating systems as supported until the native Bluetooth backends have been developed and tested.

## Requirements

Supported device: CMF Buds 2 (currently hardware-tested). Linux Bluetooth stack (BlueZ) and RFCOMM must work. The app does not require an online user account or cloud access; APT may need internet during installation. Certain earbuds settings remain phone-only.
