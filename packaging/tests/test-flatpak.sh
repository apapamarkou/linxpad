#!/usr/bin/env bash
# Test Flatpak bundle installation.
# Usage: test-flatpak.sh <flatpak-file>
set -euo pipefail

FLATPAK_FILE="${1:-}"

[[ -f "$FLATPAK_FILE" ]] || { echo "✗ Flatpak not found: $FLATPAK_FILE"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

FLATPAK_NAME="$(basename "$FLATPAK_FILE")"
echo "→ Testing $FLATPAK_NAME"

docker run --rm \
    --privileged \
    -v "$FLATPAK_FILE:/tmp/$FLATPAK_NAME:ro" \
    ubuntu:24.04 \
    bash -euo pipefail -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq flatpak
        flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
        flatpak install -y flathub org.freedesktop.Platform//24.08 2>&1 | tail -3
        flatpak install -y --bundle /tmp/$FLATPAK_NAME 2>&1 | tail -5
        echo '→ Verifying installation'
        flatpak list | grep linxpad
        echo 'Flatpak install OK'
        echo 'All checks passed'
    "
echo "✓ $FLATPAK_NAME — OK"
