#!/usr/bin/env bash
# Non-interactive release script — for CI use.
# Runs pre-flight checks then builds ALL packages for ALL configured versions.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$REPO_ROOT/packaging/distro-versions.conf"
VERSION="$(grep '^version' "$REPO_ROOT/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/')"
OUTPUT="$REPO_ROOT/packaging/output"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

header() { echo -e "\n${CYAN}══════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════${NC}"; }
ok()     { echo -e "${GREEN}✓ $1${NC}"; }
warn()   { echo -e "${YELLOW}⚠ $1${NC}"; }
fail()   { echo -e "${RED}✗ $1${NC}"; }

# Read comma-separated versions from conf
conf_versions() { grep "^$1=" "$CONF" | cut -d= -f2 | tr ',' ' '; }

header "LinxPad Release — v$VERSION (CI)"

# ── Pre-flight checks ─────────────────────────────────────────────────────
header "Pre-flight checks"

echo "→ Lint"
ruff check src/ tests/ && black --check src/ tests/ && ok "Lint passed" || { fail "Lint failed"; exit 1; }

echo "→ Tests"
pytest tests/ -q && ok "Tests passed" || { fail "Tests failed"; exit 1; }

echo "→ Git status"
if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
    fail "Uncommitted changes — commit before releasing"
    exit 1
fi
ok "Working tree clean"

mkdir -p "$OUTPUT"

# ── Build all packages ────────────────────────────────────────────────────
run() {
    local label="$1"; shift
    header "Building: $label"
    local rc=0
    bash "$@" || rc=$?
    if   [[ $rc -eq 0 ]]; then ok "$label done"
    elif [[ $rc -eq 2 ]]; then warn "$label skipped — tool not available on this host"
    else fail "$label failed"
    fi
}

run "Source tarball"  "$SCRIPTS/build-src-tarball.sh"
run "Binary tarball"  "$SCRIPTS/build-tarball.sh"
run "Arch PKGBUILD"   "$SCRIPTS/build-arch-pkgbuild.sh"
run "AppImage"        "$SCRIPTS/build-appimage.sh"

for ver in $(conf_versions "opensuse-versions"); do
    run "openSUSE $ver RPM" "$SCRIPTS/build-opensuse-rpm.sh" "$ver"
done

for ver in $(conf_versions "fedora-versions"); do
    run "Fedora $ver RPM" "$SCRIPTS/build-fedora-rpm.sh" "$ver"
done

for ver in $(conf_versions "debian-versions"); do
    run "Debian $ver .deb" "$SCRIPTS/build-deb.sh" "$ver"
done

for ver in $(conf_versions "ubuntu-versions"); do
    run "Ubuntu $ver .deb" "$SCRIPTS/build-deb.sh" "$ver"
done

# ── Test packages ────────────────────────────────────────────────────────
bash "$SCRIPTS/test-packages.sh"

# ── Summary ───────────────────────────────────────────────────────────────
header "Output"
ls -lh "$OUTPUT"/ 2>/dev/null || warn "No output files found"
ok "Release v$VERSION complete"
