#!/usr/bin/env bash
# Build a Flatpak bundle inside a Docker container.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
APP_ID="io.github.apapamarkou.linxpad"

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

# Pre-build linxpad wheel on host
WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q
WHEEL_NAME="$(basename "$WHEEL_DIR"/linxpad-*.whl)"

# Write inner build script
INNER_SCRIPT="$(mktemp)"
cat > "$INNER_SCRIPT" << INNEREOF
#!/usr/bin/env bash
set -euo pipefail

apt-get update -qq
apt-get install -y -qq flatpak flatpak-builder elfutils python3-pip python3-yaml

# Install Freedesktop SDK
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08

# Download all dependency wheels (network available here, not inside sandbox)
WDIR=/tmp/all-wheels
mkdir -p \$WDIR
pip3 download --no-deps --dest \$WDIR PyQt6 PyQt6-sip PyQt6-Qt6 watchdog
cp /wheels/$WHEEL_NAME \$WDIR/

# Build a staging source tree with wheels included
mkdir -p /tmp/flatpak-src/packaging/wheels
cp -r /src/. /tmp/flatpak-src/
cp \$WDIR/*.whl /tmp/flatpak-src/packaging/wheels/

# Rewrite manifest entirely in Python — no sed, no ambiguity
python3 << 'PYEOF'
import glob, os, yaml

with open('/src/packaging/flatpak/io.github.apapamarkou.linxpad.yaml') as f:
    m = yaml.safe_load(f)

wdir = '/tmp/all-wheels'

for mod in m['modules']:
    name = mod['name']
    if name == 'python3-pyqt6':
        wheels = (glob.glob(f'{wdir}/PyQt6-*.whl') +
                  glob.glob(f'{wdir}/pyqt6-*.whl') +
                  glob.glob(f'{wdir}/PyQt6_sip-*.whl') +
                  glob.glob(f'{wdir}/pyqt6_sip-*.whl') +
                  glob.glob(f'{wdir}/PyQt6_Qt6-*.whl') +
                  glob.glob(f'{wdir}/pyqt6_qt6-*.whl'))
        paths = ' '.join(f'packaging/wheels/{os.path.basename(w)}' for w in wheels)
        mod['build-commands'] = [f'pip3 install --prefix=/app --no-deps {paths}']
        mod['sources'] = [{'type': 'dir', 'path': '/tmp/flatpak-src'}]
    elif name == 'python3-watchdog':
        wheels = glob.glob(f'{wdir}/watchdog-*.whl')
        paths = ' '.join(f'packaging/wheels/{os.path.basename(w)}' for w in wheels)
        mod['build-commands'] = [f'pip3 install --prefix=/app --no-deps {paths}']
        mod['sources'] = [{'type': 'dir', 'path': '/tmp/flatpak-src'}]
    elif name == 'linxpad':
        linxpad_whl = os.path.basename(glob.glob(f'{wdir}/linxpad-*.whl')[0])
        mod['build-commands'][0] = f'pip3 install --prefix=/app --no-deps packaging/wheels/{linxpad_whl}'
        # Update source path
        for src in mod.get('sources', []):
            if src.get('type') == 'dir':
                src['path'] = '/tmp/flatpak-src'

with open('/tmp/manifest.yaml', 'w') as f:
    yaml.dump(m, f, default_flow_style=False)
PYEOF

REPO=/tmp/flatpak-repo
mkdir -p \$REPO

flatpak-builder \
    --repo=\$REPO \
    --force-clean \
    --disable-rofiles-fuse \
    /tmp/flatpak-build \
    /tmp/manifest.yaml

flatpak build-bundle \
    \$REPO \
    /output/LinxPad-$VERSION.flatpak \
    $APP_ID

echo "✓ Flatpak bundle created"
INNEREOF

echo "→ Building Flatpak in Docker"
docker run --rm \
    --privileged \
    -v "$REPO_ROOT:/src:ro,z" \
    -v "$OUTPUT:/output:z" \
    -v "$WHEEL_DIR:/wheels:ro,z" \
    -v "$INNER_SCRIPT:/build-inner.sh:ro,z" \
    ubuntu:24.04 \
    bash /build-inner.sh

rm -rf "$WHEEL_DIR" "$INNER_SCRIPT"

echo "✓ $OUTPUT/LinxPad-$VERSION.flatpak"
