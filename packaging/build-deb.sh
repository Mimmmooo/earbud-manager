#!/usr/bin/env bash
# Build a self-contained (no pip/venv required) Ubuntu Debian package.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || {
  echo "Unsupported VERSION: $VERSION" >&2
  exit 1
}
command -v dpkg-deb >/dev/null || { echo "Install dpkg-dev first." >&2; exit 1; }
for path in src/earbuds_manager.py src/nothing_protocol.py \
            packaging/earbud-manager packaging/io.github.earbudmanager.App.desktop LICENSE; do
  [[ -f "$ROOT/$path" ]] || { echo "Missing $path" >&2; exit 1; }
done

DEB_VERSION="${VERSION/-rc/~rc}-1"
PKG="earbud-manager_${DEB_VERSION}_all.deb"
OUT="${1:-$ROOT/dist}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf -- "$STAGE"' EXIT
chmod 755 "$STAGE"

install -d -m 755 "$STAGE/DEBIAN" "$STAGE/opt/earbud-manager/src" \
  "$STAGE/usr/bin" "$STAGE/usr/share/applications" "$STAGE/usr/share/doc/earbud-manager"
install -m 644 "$ROOT/src/earbuds_manager.py" "$STAGE/opt/earbud-manager/src/"
install -m 644 "$ROOT/src/nothing_protocol.py" "$STAGE/opt/earbud-manager/src/"
install -m 755 "$ROOT/packaging/earbud-manager" "$STAGE/usr/bin/earbud-manager"
install -m 644 "$ROOT/packaging/io.github.earbudmanager.App.desktop" \
  "$STAGE/usr/share/applications/io.github.earbudmanager.App.desktop"
install -m 644 "$ROOT/LICENSE" "$STAGE/usr/share/doc/earbud-manager/copyright"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: earbud-manager
Version: $DEB_VERSION
Section: sound
Priority: optional
Architecture: all
Maintainer: Earbud Manager contributors <noreply@github.com>
Depends: python3, python3-gi, python3-gi-cairo, python3-cairo, gir1.2-gtk-4.0, gir1.2-adw-1, bluez
Description: Unofficial GNOME manager for supported Bluetooth earbuds
 Manage CMF/Nothing earbud battery, ANC, latency and multipoint
 using BlueZ RFCOMM on Ubuntu GNOME.
EOF

# Debian packages use /usr/bin and /usr/share, never system /usr/local.
# The source installer intentionally remains separate.
dpkg-deb --root-owner-group --build "$STAGE" "$OUT/$PKG"
dpkg-deb --info "$OUT/$PKG"
echo "Built: $OUT/$PKG"
