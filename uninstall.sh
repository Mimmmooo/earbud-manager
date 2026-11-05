#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "${EUID}" -eq 0 ]]; then
  echo 'Run as a regular user: ./uninstall.sh' >&2
  exit 1
fi
# Do not modify files owned by the .deb package manager.
if command -v dpkg-query >/dev/null 2>&1 &&
   [[ "$(dpkg-query -W -f='\x24{Status}' earbud-manager 2>/dev/null || true)" == "install ok installed" ]]; then
  echo 'A .deb installation is present. Use APT to update/remove it; do not mix installation methods.' >&2
  exit 1
fi

printf 'Remove the installed Earbud Manager app? Local settings will be kept.\n'
read -r -p 'Uninstall? [y/N] ' answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo 'Cancelled.'; exit 0; }
sudo rm -f /usr/local/bin/earbud-manager
sudo rm -f /usr/local/share/applications/io.github.earbudmanager.App.desktop
sudo rm -f /usr/local/share/applications/io.github.earbudmanager.App.desktop~
sudo rm -rf -- /opt/earbud-manager
sudo rm -f /usr/local/bin/universal-earbuds-manager
sudo rm -f /usr/local/share/applications/io.github.universalearbuds.Manager.desktop
sudo rm -rf -- /opt/universal-earbuds-manager
if command -v update-desktop-database >/dev/null 2>&1; then
  sudo update-desktop-database /usr/local/share/applications || true
fi
printf 'Removed. Local settings remain in ~/.config/earbuds-manager/.\n'
