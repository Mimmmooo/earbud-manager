#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as your regular user: ./install.sh (sudo is invoked only when needed)." >&2
  exit 1
fi

# Do not modify files owned by the .deb package manager.
if command -v dpkg-query >/dev/null 2>&1 &&
   [[ "$(dpkg-query -W -f='\x24{Status}' earbud-manager 2>/dev/null || true)" == "install ok installed" ]]; then
  echo 'A .deb installation is present. Use APT to update/remove it; do not mix installation methods.' >&2
  exit 1
fi

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for required in src/earbuds_manager.py src/nothing_protocol.py; do
  [[ -f "$SOURCE_DIR/$required" ]] || { echo "Missing $required" >&2; exit 1; }
done

printf 'This installs application code under /opt/earbud-manager,\n'
printf 'a launcher under /usr/local/bin and an app-menu entry.\n'
printf 'Your personal settings in ~/.config/earbuds-manager remain untouched.\n'
read -r -p 'Install system-wide? [y/N] ' reply
[[ "$reply" =~ ^[Yy]$ ]] || { echo 'Cancelled.'; exit 0; }

sudo apt-get update
sudo apt-get install -y python3 python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-4.0 gir1.2-adw-1 bluez

sudo install -d -m 755 /opt/earbud-manager/src
sudo install -m 644 "$SOURCE_DIR/src/earbuds_manager.py" /opt/earbud-manager/src/earbuds_manager.py
sudo install -m 644 "$SOURCE_DIR/src/nothing_protocol.py" /opt/earbud-manager/src/nothing_protocol.py
sudo install -d -m 755 /usr/local/bin /usr/local/share/applications
sudo install -m 755 "$SOURCE_DIR/packaging/earbud-manager" /usr/local/bin/earbud-manager
sudo install -m 644 "$SOURCE_DIR/packaging/io.github.earbudmanager.App.desktop" /usr/local/share/applications/io.github.earbudmanager.App.desktop

# Remove previous Universal Earbuds Manager launchers after installing the new app.
# The user-local configuration directory is intentionally preserved.
sudo rm -f /usr/local/bin/universal-earbuds-manager
sudo rm -f /usr/local/share/applications/io.github.universalearbuds.Manager.desktop
sudo rm -rf -- /opt/universal-earbuds-manager

if command -v update-desktop-database >/dev/null 2>&1; then
  sudo update-desktop-database /usr/local/share/applications || true
fi
printf '\nInstalled! Open Applications → Earbud Manager, or run:\n'
printf '  earbud-manager\n'
printf 'You can delete the downloaded ZIP and extracted project afterward.\n'
