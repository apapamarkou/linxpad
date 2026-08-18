#!/usr/bin/env bash
# Build a self-contained fat AppImage using python-appimage.
# Bundles Python 3.11, PyQt6 + Qt6 libs, watchdog, and linxpad.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

# Build the reusable builder image if not already present
BUILDER_IMAGE="linxpad-builder:4"
if ! docker image inspect "$BUILDER_IMAGE" >/dev/null 2>&1; then
    echo "→ Building reusable builder image (one-time, takes a few minutes)"
    DOCKERFILE="$(mktemp)"
    cat > "$DOCKERFILE" << 'DOCKEREOF'
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq \
    python3 python3-pip python3-dev wget file patchelf binutils \
    libfuse2 desktop-file-utils squashfs-tools \
    libglib2.0-0 libpcre3 libpcre2-8-0 \
    libxcb-cursor0 libxcb-render-util0 libxcb-image0 libxcb-shm0 libxcb-util1 \
    libxcb1 libxau6 libxdmcp6 libbsd0 libxkbcommon0 libxkbcommon-x11-0 \
    libegl1 libgl1 libdbus-1-3 libx11-6 libx11-xcb1 \
    libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libxcb-randr0 \
    libxcb-xfixes0 libxcb-sync1 libxcb-xkb1 libxcb-glx0 \
    && python3 -m pip install --quiet --break-system-packages python-appimage \
    && wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage \
        -O /usr/local/bin/appimagetool \
    && chmod +x /usr/local/bin/appimagetool \
    && rm -rf /var/lib/apt/lists/*
DOCKEREOF
    docker build --load -t "$BUILDER_IMAGE" -f "$DOCKERFILE" "$(dirname "$DOCKERFILE")"
    rm -f "$DOCKERFILE"
fi

mkdir -p "$OUTPUT"

# Pre-build wheel on host
WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q
WHEEL_NAME="$(basename "$WHEEL_DIR"/linxpad-*.whl)"

# Pre-download all dependency wheels on the host (reliable network)
echo "→ Pre-downloading dependency wheels on host"
python3 -m pip download PyQt6 PyQt6-sip PyQt6-Qt6 watchdog -d "$WHEEL_DIR" -q

# Build python-appimage metadata directory
APPIMG_META="$(mktemp -d)"
cat > "$APPIMG_META/requirements.txt" << EOF
PyQt6>=6.4
watchdog>=3.0
local+linxpad
EOF

cat > "$APPIMG_META/entrypoint.sh" << 'EOF'
#! /bin/bash
QT6LIB="${APPDIR}/opt/python3.11/lib/python3.11/site-packages/PyQt6/Qt6/lib"
export LD_LIBRARY_PATH="${APPDIR}/usr/lib:${QT6LIB}"
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

# Patch python-appimage to use pre-downloaded wheels (it runs pip with --isolated
# so env vars and pip.conf are ignored; patch the source directly)
cat > /tmp/patch_appimage.py << 'PYEOF'
import python_appimage.commands.build.app as m, inspect, re
src = inspect.getfile(m)
with open(src) as f:
    code = f.read()
patched = re.sub(
    r"(system\(\('./AppDir/AppRun'[^)]*?'pip'[^)]*?'install'[^)]*?in_tree_build,)",
    r"\1 '--find-links', '/wheels',",
    code, flags=re.DOTALL
)
with open(src, 'w') as f:
    f.write(patched)
print('patched:', src)
PYEOF
python3 /tmp/patch_appimage.py

# Install linxpad so python-appimage can find it via local+
python3 -m pip install --quiet --break-system-packages --no-deps \\
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

# Remove any bundled glibc — it must always come from the host
rm -f \$APPDIR/usr/lib/libc.so* \$APPDIR/usr/lib/libm.so* \$APPDIR/usr/lib/libdl.so* \
       \$APPDIR/usr/lib/libpthread.so* \$APPDIR/usr/lib/librt.so* \$APPDIR/usr/lib/libutil.so* \
       \$APPDIR/usr/lib/ld-linux*.so*

# Bundle all system libs needed by PyQt6/Qt6 that aren't already inside the AppImage
mkdir -p \$APPDIR/usr/lib

# Explicitly copy all required libs (both ldd-visible and dlopen-loaded)
# NOTE: never bundle libc, libm, libdl, libpthread, ld-linux — must come from host
for lib in \
    libglib-2.0.so.0 libgthread-2.0.so.0 libgmodule-2.0.so.0 libgobject-2.0.so.0 \
    libpcre.so.3 libpcre2-8.so.0 \
    libxcb-cursor.so.0 libxcb-render-util.so.0 libxcb-render.so.0 \
    libxcb-image.so.0 libxcb-shm.so.0 libxcb-util.so.1 \
    libxcb.so.1 libXau.so.6 libXdmcp.so.6 libbsd.so.0 libmd.so.0 \
    libxkbcommon.so.0 libxkbcommon-x11.so.0 \
    libdbus-1.so.3; do
    src=\$(find /usr/lib /usr/lib/x86_64-linux-gnu /lib /lib/x86_64-linux-gnu -name "\$lib" 2>/dev/null | head -1 || true)
    [ -n "\$src" ] && cp -L "\$src" \$APPDIR/usr/lib/ && echo "  bundled \$lib" || echo "  ⚠ not found: \$lib"
done

# Auto-discover remaining deps via ldd on all PyQt6 .so files
# Skip glibc internals that must come from the host
apt-get install -y -qq binutils 2>/dev/null
SKIP_PATTERN='/(libc|libm|libdl|libpthread|librt|libresolv|libnss|libutil|ld-linux|libgcc_s)\.so'
find \$APPDIR/opt/python3.11/lib/python3.11/site-packages/PyQt6 -name '*.so*' | while read -r so; do
    ldd "\$so" 2>/dev/null | awk '/=> \//{print \$3}' | while read -r dep; do
        [[ "\$dep" == \$APPDIR/* ]] && continue
        echo "\$dep" | grep -qE "\$SKIP_PATTERN" && continue
        [ -f "\$dep" ] && cp -Ln "\$dep" \$APPDIR/usr/lib/ 2>/dev/null || true
    done
done

# Verify libxcb-cursor was actually bundled (hard requirement for Qt6 >= 6.5)
if [ ! -f \$APPDIR/usr/lib/libxcb-cursor.so.0 ]; then
    echo "✗ libxcb-cursor.so.0 was not found and could not be bundled" >&2
    exit 1
fi

# Patch RPATH of libqxcb.so so dlopen finds bundled libxcb-cursor via \$ORIGIN.
# platforms/ is 9 levels deep from APPDIR root, so 9 x ../ reaches usr/lib.
XCB_PLUGIN=\$(find \$APPDIR -name "libqxcb.so" 2>/dev/null | head -1)
if [ -n "\$XCB_PLUGIN" ]; then
    patchelf --set-rpath '\$ORIGIN/../../../../../../../../../usr/lib' "\$XCB_PLUGIN"
fi

# Patch AppRun: insert LD_LIBRARY_PATH after APPDIR is set
sed -i 's|# Call the application entry point|QT6LIB="\${APPDIR}/opt/python3.11/lib/python3.11/site-packages/PyQt6/Qt6/lib"\nexport LD_LIBRARY_PATH="\${APPDIR}/usr/lib:\${QT6LIB}"\n# Call the application entry point|' \$APPDIR/AppRun
# Repack
ARCH=x86_64 appimagetool \$APPDIR /output/LinxPad-${VERSION}-x86_64.AppImage
INNEREOF

echo "→ Building fat AppImage in Docker (downloads base image — takes a few minutes)"
docker run --rm \
    --privileged \
    --network host \
    -v "$REPO_ROOT:/src:ro,z" \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/wheels:ro,z" \
    -v "$APPIMG_META:/appmeta:ro,z" \
    -v "$INNER_SCRIPT:/build-inner.sh:ro,z" \
    "$BUILDER_IMAGE" \
    bash /build-inner.sh

rm -rf "$WHEEL_DIR" "$APPIMG_META" "$INNER_SCRIPT"

echo "✓ Fat AppImage in $OUTPUT/"
