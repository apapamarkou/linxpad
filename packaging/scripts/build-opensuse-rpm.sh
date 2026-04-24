#!/usr/bin/env bash
# Build openSUSE RPM inside a Docker container.
# Usage: build-opensuse-rpm.sh [leap|tumbleweed]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
CONF="$REPO_ROOT/packaging/distro-versions.conf"

SUSE_VER="${1:-$(grep '^opensuse-versions=' "$CONF" | cut -d= -f2 | cut -d, -f1)}"
case "$SUSE_VER" in
    tumbleweed) IMAGE="opensuse/tumbleweed" ;;
    *)          IMAGE="opensuse/leap:$SUSE_VER" ;;
esac

command -v docker >/dev/null 2>&1 || { echo "⚠ docker not found — skipping"; exit 2; }

mkdir -p "$OUTPUT"

echo "→ Building openSUSE $SUSE_VER RPM in Docker"

# Pre-build the wheel on the host so the container doesn't need hatchling
WHEEL_DIR="$(mktemp -d)"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$WHEEL_DIR" -q
WHEEL="$(ls "$WHEEL_DIR"/linxpad-*.whl)"

docker run --rm \
    -v "$REPO_ROOT:/src:ro" \
    -v "$OUTPUT:/output" \
    -v "$WHEEL_DIR:/wheels:ro" \
    "$IMAGE" \
    bash -euo pipefail -c "
        zypper install -y rpm-build python3-pip git python3-rpm-macros
        git config --global --add safe.directory /src
        RPMBUILD=/tmp/rpmbuild
        mkdir -p \$RPMBUILD/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
        git -C /src archive --format=tar.gz --prefix=linxpad-$VERSION/ HEAD \
            -o \$RPMBUILD/SOURCES/linxpad-$VERSION.tar.gz
        cp /src/packaging/specs/linxpad.spec \$RPMBUILD/SPECS/
        # Patch spec to install from pre-built wheel instead of building from source
        sed -i 's|python3 -m pip install --no-build-isolation --prefix=%{buildroot}%{_prefix} .|pip3 install --no-deps --prefix=%{buildroot}%{_prefix} /wheels/linxpad-*.whl|' \$RPMBUILD/SPECS/linxpad.spec
        sed -i 's|python3 -m pip install --no-build-isolation --root=%{buildroot} --prefix=%{_prefix} .|pip3 install --no-deps --root=%{buildroot} --prefix=%{_prefix} /wheels/linxpad-*.whl|' \$RPMBUILD/SPECS/linxpad.spec
        sed -i 's|Requires:.*python3-pyqt6.*|Requires:       python3-qt6 >= 6.4|' \$RPMBUILD/SPECS/linxpad.spec
        rpmbuild -ba \
            --define '_topdir '\$RPMBUILD \
            --define 'dist .opensuse${SUSE_VER}' \
            \$RPMBUILD/SPECS/linxpad.spec
        find \$RPMBUILD/RPMS \$RPMBUILD/SRPMS -name '*.rpm' -exec cp {} /output/ \;
    "
rm -rf "$WHEEL_DIR"

echo "✓ openSUSE $SUSE_VER RPM in $OUTPUT/"
