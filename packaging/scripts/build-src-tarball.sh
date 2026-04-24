#!/usr/bin/env bash
# Build a source tarball: linxpad-VERSION.tar.gz
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"
NAME="linxpad-$VERSION"

mkdir -p "$OUTPUT"

echo "→ Building source tarball $NAME.tar.gz"
git -C "$REPO_ROOT" archive --format=tar.gz --prefix="$NAME/" HEAD \
    -o "$OUTPUT/$NAME.tar.gz"

echo "✓ $OUTPUT/$NAME.tar.gz"
