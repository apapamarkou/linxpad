#!/usr/bin/env bash
# Test RPM installation on openSUSE.
# Usage: test-opensuse-rpm.sh <rpm-file> [suse-version]
set -euo pipefail

RPM_FILE="${1:-}"
SUSE_VER="${2:-tumbleweed}"

[[ -f "$RPM_FILE" ]] || { echo "✗ RPM not found: $RPM_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

case "$SUSE_VER" in
    tumbleweed) IMAGE="opensuse/tumbleweed" ;;
    *)          IMAGE="opensuse/leap:$SUSE_VER" ;;
esac

RPM_NAME="$(basename "$RPM_FILE")"
echo "→ Testing $RPM_NAME on openSUSE $SUSE_VER"

docker run --rm \
    -v "$RPM_FILE:/tmp/$RPM_NAME:ro" \
    "$IMAGE" \
    bash -euo pipefail -c "
        zypper --no-gpg-checks install -y /tmp/$RPM_NAME 2>&1 | tail -5
        echo '→ Verifying installation'
        rpm -q linxpad
        python3 -c 'import linxpad.core; print(\"linxpad core import OK\")'
        test -f /usr/bin/linxpad && echo 'linxpad binary OK'
        test -f /usr/share/applications/linxpad.desktop && echo 'desktop file OK'
        test -f /usr/share/icons/hicolor/256x256/apps/linxpad.png && echo 'icon OK'
        echo 'All checks passed'
    "
echo "✓ $RPM_NAME on openSUSE $SUSE_VER — OK"
