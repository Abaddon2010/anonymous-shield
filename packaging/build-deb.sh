#!/bin/sh
# Anonymous Shield — monta o .deb (sem root p/ construir; só dpkg-deb).
# Uso: sh packaging/build-deb.sh   (rode na raiz do repo Test/)
# Saída: anonymous-shield/deb-out/anonymous-shield_<ver>_amd64.deb
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
ROOT="$(pwd)"
VER="$(python3 -c "import re;print(re.search(r'__version__ *= *\"([^\"]+)\"', open('anonymous-shield/anonshield/__init__.py').read()).group(1))")"
STAGE="$(mktemp -d)/anonshield-deb"
OUT="anonymous-shield/deb-out"
rm -rf "$OUT"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt/anonymous-shield" \
  "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/256x256/apps" "$OUT"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: anonymous-shield
Version: $VER
Section: net
Priority: optional
Architecture: amd64
Depends: python3, python3-pyqt6, python3-stem, python3-requests, python3-socks, python3-cryptography, tor, obfs4proxy, nftables
Recommends: gsettings-desktop-schemas
Maintainer: Abaddon2010 <Abaddon2010@users.noreply.github.com>
Description: Tor desktop client (PyQt6 + system tor)
 Onion button with bootstrap progress, bridges, SOCKS, DNSCrypt,
 total protection and in-app updates. Uses the system Tor on Linux.
EOF

cp -r anonymous-shield/main.py anonymous-shield/anonshield "$STAGE/opt/anonymous-shield/"
cp -r anonymous-shield/assets "$STAGE/opt/anonymous-shield/"
cp -r anonymous-shield/vendor "$STAGE/opt/anonymous-shield/"
cp LICENSE LICENSE-APACHE "$STAGE/opt/anonymous-shield/"
find "$STAGE/opt/anonymous-shield" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

cat > "$STAGE/usr/bin/anonymous-shield" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /opt/anonymous-shield/main.py "$@"
EOF
chmod 755 "$STAGE/usr/bin/anonymous-shield"

cat > "$STAGE/usr/share/applications/anonymous-shield.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Anonymous Shield
Comment=Tor desktop client
Exec=/usr/bin/anonymous-shield
Icon=anonymous-shield
Terminal=false
Categories=Network;Security;
EOF

cp anonymous-shield/assets/icon.png "$STAGE/usr/share/icons/hicolor/256x256/apps/anonymous-shield.png"

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
update-desktop-database >/dev/null 2>&1 || true
gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

dpkg-deb --build "$STAGE" "$OUT/anonymous-shield_${VER}_amd64.deb"
rm -rf "$(dirname "$STAGE")"
echo "OK: $OUT/anonymous-shield_${VER}_amd64.deb"
