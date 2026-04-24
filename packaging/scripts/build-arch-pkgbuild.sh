#!/usr/bin/env bash
# Generate a PKGBUILD for Arch Linux and test it with makepkg in Docker.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
PKGBUILD_DIR="$OUTPUT/arch"

mkdir -p "$PKGBUILD_DIR"

# Build a local source tarball to use inside the container
# (avoids needing the GitHub tag to exist yet)
LOCAL_TARBALL="$PKGBUILD_DIR/linxpad-$VERSION.tar.gz"
git -C "$REPO_ROOT" archive --format=tar.gz --prefix="linxpad-$VERSION/" HEAD \
    -o "$LOCAL_TARBALL"
SHA256="$(sha256sum "$LOCAL_TARBALL" | cut -d' ' -f1)"

echo "→ Generating PKGBUILD for linxpad $VERSION"
cat > "$PKGBUILD_DIR/PKGBUILD" << EOF
# Maintainer: Andrianos Papamarkou <andrianos@example.com>
pkgname=linxpad
pkgver=$VERSION
pkgrel=1
pkgdesc="A macOS-style fullscreen application launcher for Linux (X11 + Wayland)"
arch=('any')
url="https://github.com/apapamarkou/linxpad"
license=('GPL-3.0-or-later')
depends=('python>=3.11' 'python-pyqt6' 'python-watchdog')
makedepends=('python-pip' 'python-hatchling')
source=("https://github.com/apapamarkou/linxpad/archive/refs/tags/v\${pkgver}.tar.gz")
sha256sums=('$SHA256')

build() {
    cd "\$srcdir/linxpad-\$pkgver"
    python -m pip wheel --no-build-isolation --no-deps -w dist .
}

package() {
    cd "\$srcdir/linxpad-\$pkgver"
    python -m pip install --no-deps --root="\$pkgdir" --prefix=/usr dist/linxpad-*.whl
    install -Dm644 src/linxpad/icons/linxpad.png \
        "\$pkgdir/usr/share/icons/hicolor/256x256/apps/linxpad.png"
    install -Dm644 src/linxpad/icons/linxpad-folder.png \
        "\$pkgdir/usr/share/icons/hicolor/256x256/apps/linxpad-folder.png"
    install -Dm644 packaging/specs/linxpad.desktop \
        "\$pkgdir/usr/share/applications/linxpad.desktop"
    install -Dm644 LICENSE \
        "\$pkgdir/usr/share/licenses/\$pkgname/LICENSE"
}
EOF

echo "✓ PKGBUILD written to $PKGBUILD_DIR/PKGBUILD"
echo "  sha256: $SHA256"
echo "  Note: update source= URL and sha256sums after pushing the GitHub tag."

# Test with makepkg inside an Arch Docker container using the local tarball
if command -v docker >/dev/null 2>&1; then
    echo "→ Testing PKGBUILD with makepkg in Docker (archlinux)"
    docker run --rm \
        -v "$PKGBUILD_DIR:/build" \
        archlinux:latest \
        bash -euo pipefail -c "
            pacman -Sy --noconfirm base-devel python-pip python-hatchling 2>/dev/null
            useradd -m builder
            cp /build/PKGBUILD /home/builder/
            # Use local tarball instead of downloading from GitHub
            cp /build/linxpad-$VERSION.tar.gz /home/builder/
            chown -R builder /home/builder/
            cd /home/builder
            # Patch source= to use local file for testing
            sed -i 's|source=(.*)|source=(\"linxpad-$VERSION.tar.gz\")|' PKGBUILD
            sudo -u builder makepkg --noconfirm --nodeps -f
            find /home/builder -name '*.pkg.tar.zst' -exec cp {} /build/ \;
        "
    echo "✓ Arch package in $PKGBUILD_DIR/"
else
    echo "⚠ Docker not found — PKGBUILD generated but not tested"
    echo "  To build: cd $PKGBUILD_DIR && makepkg -si"
fi
