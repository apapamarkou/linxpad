#!/usr/bin/env bash
# Build a self-contained fat AppImage using python-appimage.
# Bundles Python 3.11, PyQt6 + Qt6 libs, watchdog, and linxpad.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

# Pre-build wheel on host
WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q
WHEEL_NAME="$(basename "$WHEEL_DIR"/linxpad-*.whl)"

# Build python-appimage metadata directory
APPIMG_META="$(mktemp -d)"
cat > "$APPIMG_META/requirements.txt" << EOF
PyQt6>=6.4
watchdog>=3.0
local+linxpad
EOF

cat > "$APPIMG_META/entrypoint.sh" << 'EOF'
#! /bin/bash
export LD_LIBRARY_PATH="${APPDIR}/usr/lib:${LD_LIBRARY_PATH:-}"
"${APPDIR}/usr/bin/python3" -m linxpad.main "$@"
EOF

cp "$REPO_ROOT/packaging/specs/linxpad.desktop" "$APPIMG_META/"
cp "$REPO_ROOT/src/linxpad/icons/linxpad.png"   "$APPIMG_META/"

# Write the inner build script to a file to avoid heredoc escaping issues
INNER_SCRIPT="$(mktemp)"
cat > "$INNER_SCRIPT" << INNEREOF
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq python3-pip python3-dev wget file patchelf \\
    libfuse2 desktop-file-utils squashfs-tools libglib2.0-0

pip3 install --quiet --break-system-packages python-appimage

# Install linxpad so python-appimage can find it via local+
pip3 install --quiet --break-system-packages --no-deps \\
    --target=/tmp/linxpad-pkg /wheels/$WHEEL_NAME
export PYTHONPATH=/tmp/linxpad-pkg

WORKDIR=/tmp/appimage-work
mkdir -p \$WORKDIR
cp -r /appmeta/. \$WORKDIR/appdir/

cd \$WORKDIR
python3 -m python_appimage build app \\
    --python-version 3.11 \\
    --name LinxPad \\
    appdir

# Extract to add missing system libraries
BUILT=\$(ls \$WORKDIR/LinxPad-*.AppImage 2>/dev/null | head -1)
chmod +x "\$BUILT"
"\$BUILT" --appimage-extract
APPDIR=\$WORKDIR/squashfs-root

# Bundle missing GLib shared libraries
mkdir -p \$APPDIR/usr/lib
for lib in libgthread-2.0.so.0 libglib-2.0.so.0 libgmodule-2.0.so.0 libgobject-2.0.so.0; do
    src=\$(find /usr/lib /lib -name "\$lib" 2>/dev/null | head -1 || true)
    [ -n "\$src" ] && cp -L "\$src" \$APPDIR/usr/lib/ || true
done

# Repack
wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage \\
    -O /usr/local/bin/appimagetool
chmod +x /usr/local/bin/appimagetool
ARCH=x86_64 appimagetool \$APPDIR /output/LinxPad-${VERSION}-x86_64.AppImage
INNEREOF

echo "→ Building fat AppImage in Docker (downloads base image — takes a few minutes)"
docker run --rm \
    --privileged \
    -v "$REPO_ROOT:/src:ro,z" \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/wheels:ro,z" \
    -v "$APPIMG_META:/appmeta:ro,z" \
    -v "$INNER_SCRIPT:/build-inner.sh:ro,z" \
    ubuntu:24.04 \
    bash /build-inner.sh

rm -rf "$WHEEL_DIR" "$APPIMG_META" "$INNER_SCRIPT"

echo "✓ Fat AppImage in $OUTPUT/"
