#!/usr/bin/env bash
# Test AppImage runs correctly on Ubuntu 24.04.
# Usage: test-appimage.sh <appimage-file>
set -euo pipefail

APPIMAGE="$(realpath "${1:-}")"
[[ -f "$APPIMAGE" ]] || { echo "✗ AppImage not found: $APPIMAGE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

APPIMAGE_NAME="$(basename "$APPIMAGE")"
echo "→ Testing $APPIMAGE_NAME on Ubuntu 24.04"

docker run --rm \
    --privileged \
    -v "$APPIMAGE:/tmp/$APPIMAGE_NAME" \
    ubuntu:24.04 \
    bash -euo pipefail -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq libfuse2 xvfb 2>&1 | tail -3

        chmod +x /tmp/$APPIMAGE_NAME

        echo '→ Verifying AppImage extracts cleanly'
        /tmp/$APPIMAGE_NAME --appimage-extract >/dev/null
        SROOT=/squashfs-root
        test -f \$SROOT/AppRun && echo 'AppRun OK'
        test -f \$SROOT/usr/lib/libxcb-cursor.so.0 && echo 'libxcb-cursor bundled OK'
        test -f \$SROOT/usr/lib/libpcre.so.3 && echo 'libpcre bundled OK'

        echo '→ Verifying linxpad imports inside AppImage Python'
        cat > /tmp/check_import.py << 'PYEOF'
import sys
sys.path.insert(0, '/squashfs-root/opt/python3.11/lib/python3.11/site-packages')
import linxpad.core
print('linxpad core import OK')
PYEOF
        QT6LIB=\$SROOT/opt/python3.11/lib/python3.11/site-packages/PyQt6/Qt6/lib
        LD_LIBRARY_PATH="\$SROOT/usr/lib:\$QT6LIB" \
        \$SROOT/opt/python3.11/bin/python3.11 /tmp/check_import.py

        echo '→ ldd on libqxcb.so'
        find \$SROOT -name libqxcb.so -exec ldd {} \;

        echo '→ Running AppImage under Xvfb (5 second smoke test)'
        Xvfb :99 -screen 0 1024x768x24 &
        XVFB_PID=\$!
        sleep 1
        DISPLAY=:99 timeout 5 /tmp/$APPIMAGE_NAME || code=\$?
        kill \$XVFB_PID 2>/dev/null || true
        # timeout exits 124 on timeout (expected — app kept running), anything else is a real failure
        if [[ \${code:-0} -ne 0 && \${code:-0} -ne 124 ]]; then
            echo \"✗ AppImage exited with code \${code}\" >&2
            exit 1
        fi

        echo 'All checks passed'
    "
echo "✓ $APPIMAGE_NAME on Ubuntu 24.04 — OK"
