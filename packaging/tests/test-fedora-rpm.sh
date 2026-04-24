#!/usr/bin/env bash
# Test RPM installation on Fedora.
# Usage: test-fedora-rpm.sh <rpm-file> [fedora-version]
set -euo pipefail

RPM_FILE="${1:-}"
FEDORA_VER="${2:-43}"

[[ -f "$RPM_FILE" ]] || { echo "✗ RPM not found: $RPM_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

RPM_NAME="$(basename "$RPM_FILE")"
echo "→ Testing $RPM_NAME on Fedora $FEDORA_VER"

docker run --rm \
    -v "$RPM_FILE:/tmp/$RPM_NAME:ro" \
    "fedora:$FEDORA_VER" \
    bash -euo pipefail -c "
        dnf install -y /tmp/$RPM_NAME 2>&1 | tail -5
        echo '→ Verifying installation'
        rpm -q linxpad
        python3 -c 'import linxpad.core; print(\"linxpad core import OK\")'
        test -f /usr/bin/linxpad && echo 'linxpad binary OK'
        test -f /usr/share/applications/linxpad.desktop && echo 'desktop file OK'
        test -f /usr/share/icons/hicolor/256x256/apps/linxpad.png && echo 'icon OK'
        echo 'All checks passed'
    "
echo "✓ $RPM_NAME on Fedora $FEDORA_VER — OK"
