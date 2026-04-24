#!/usr/bin/env bash
# Build a binary tarball for generic Linux: linxpad-VERSION-linux.tar.gz
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
NAME="linxpad-$VERSION-linux"
STAGING="$OUTPUT/$NAME"

mkdir -p "$OUTPUT"
rm -rf "$STAGING"
mkdir -p "$STAGING"

echo "→ Building wheel"
python3 -m pip wheel "$REPO_ROOT" --no-deps -w "$STAGING/wheels"

echo "→ Copying assets"
cp "$REPO_ROOT/packaging/specs/linxpad.desktop"        "$STAGING/"
cp "$REPO_ROOT/src/linxpad/icons/linxpad.png"          "$STAGING/"
cp "$REPO_ROOT/src/linxpad/icons/linxpad-folder.png"   "$STAGING/"
cp "$REPO_ROOT/README.md"                              "$STAGING/"
cp "$REPO_ROOT/install"                                "$STAGING/install"
chmod +x "$STAGING/install"

echo "→ Creating tarball"
tar -czf "$OUTPUT/$NAME.tar.gz" -C "$OUTPUT" "$NAME"
rm -rf "$STAGING"

echo "✓ $OUTPUT/$NAME.tar.gz"
