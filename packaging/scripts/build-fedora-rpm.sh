#!/usr/bin/env bash
# Build Fedora RPM inside a Docker container.
# Usage: build-fedora-rpm.sh [fedora-version]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
CONF="$REPO_ROOT/packaging/distro-versions.conf"

FEDORA_VER="${1:-$(grep '^fedora-versions=' "$CONF" | cut -d= -f2 | cut -d, -f1)}"

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

echo "→ Building Fedora $FEDORA_VER RPM in Docker"

WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q

docker run --rm \
    -v "$REPO_ROOT:/src:ro" \
    -v "$OUTPUT:/output" \
    -v "$WHEEL_DIR:/wheels:ro" \
    "fedora:$FEDORA_VER" \
    bash -euo pipefail -c "
        dnf install -y rpm-build python3-pip git python3-rpm-macros
        git config --global --add safe.directory /src
        RPMBUILD=/tmp/rpmbuild
        mkdir -p \$RPMBUILD/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
        git -C /src archive --format=tar.gz --prefix=linxpad-$VERSION/ HEAD \
            -o \$RPMBUILD/SOURCES/linxpad-$VERSION.tar.gz
        cp /src/packaging/specs/linxpad.spec \$RPMBUILD/SPECS/
        sed -i 's|python3 -m pip install --no-build-isolation --prefix=%{buildroot}%{_prefix} .|pip3 install --no-deps --prefix=%{buildroot}%{_prefix} /wheels/linxpad-*.whl|' \$RPMBUILD/SPECS/linxpad.spec
        sed -i 's|python3 -m pip install --no-build-isolation --root=%{buildroot} --prefix=%{_prefix} .|pip3 install --no-deps --root=%{buildroot} --prefix=%{_prefix} /wheels/linxpad-*.whl|' \$RPMBUILD/SPECS/linxpad.spec
        rpmbuild -ba \
            --define '_topdir '\$RPMBUILD \
            --define 'dist .fc$FEDORA_VER' \
            \$RPMBUILD/SPECS/linxpad.spec
        find \$RPMBUILD/RPMS \$RPMBUILD/SRPMS -name '*.rpm' -exec cp {} /output/ \;
    "
rm -rf "$WHEEL_DIR"

echo "✓ Fedora $FEDORA_VER RPM in $OUTPUT/"
