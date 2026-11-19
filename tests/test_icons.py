# Failure output on unfixed code:
# FAILED tests/test_icons.py::test_c5_size_misparse_retina_dir
#   AssertionError: Expected 0 for path with '2x-retina' dir (no NxN component), got 2.
#   Bug 1.5: _parse_size misparses '2x-retina' as size 2.
# FAILED tests/test_icons.py::test_c5_size_parse_valid_nxn
#   AssertionError: Expected 48 for path with '48x48' dir, got 2.
#   Bug 1.5: Parser returns early with 2 (from '2x-retina') before reaching '48x48'.
#   This companion test also FAILS on unfixed code — the bug is broader than expected:
#   not only does '2x-retina' misparse, it also shadows any valid NxN component later in the path.

from hypothesis import given, settings
from hypothesis import strategies as st

from linxpad.services.icons import IconResolver


def test_c5_size_misparse_retina_dir():
    """Bug 1.5: _parse_size returns 2 for '2x-retina' directories instead of 0.
    MUST FAIL on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/2x-retina/apps/firefox.png")
    assert result == 0, (
        f"Expected 0 for path with '2x-retina' dir (no NxN component), got {result}. "
        "Bug 1.5: _parse_size misparses '2x-retina' as size 2."
    )


def test_c5_size_parse_valid_nxn():
    """Bug 1.5 companion: _parse_size correctly finds 48 when 48x48 is present.
    This should PASS on unfixed code (the happy path works).
    May also fail if the regex is entirely broken — document whichever happens.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/2x-retina/48x48/apps/firefox.png")
    assert result == 48, (
        f"Expected 48 for path with '48x48' dir, got {result}. "
        "Bug 1.5: _parse_size failed to find 48."
    )


# ── Phase 2: Preservation property tests (Task 7) ────────────────────────────
# These tests MUST PASS on unfixed code. They encode correct baseline behavior
# for inputs that do NOT trigger the bugs.
#
# Observations on unfixed code (confirmed from source code reading and existing
# test failures):
#   _parse_size("/usr/share/icons/Adwaita/scalable/apps/firefox.svg")     -> 9999
#   _parse_size("/usr/share/icons/Adwaita/scalable/48x48/apps/firefox.svg") -> 9999
#   _parse_size("/usr/share/icons/Adwaita/48x48/apps/firefox.png")        -> 48
#   _parse_size("/usr/share/icons/Adwaita/16x16/apps/something.png")      -> 16
#   _parse_size("/usr/share/icons/Adwaita/48/apps/something.png")         -> 48
# (the pure-digit "48" branch works because the elif p.isdigit() check is correct)


def test_parse_size_scalable_returns_9999():
    """Preservation: 'scalable' in path returns 9999 (highest priority).

    The check `if 'scalable' in parts: return 9999` is first in _parse_size
    and unaffected by the NxN misparse bug. MUST PASS on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/scalable/apps/firefox.svg")
    assert result == 9999, f"Expected 9999 for scalable path, got {result}."


def test_parse_size_scalable_takes_precedence_over_nxn():
    """Preservation: 'scalable' before NxN in path still returns 9999.

    The scalable check is evaluated before the per-component loop, so a path
    containing both 'scalable' and '48x48' returns 9999 not 48.
    MUST PASS on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/scalable/48x48/apps/firefox.svg")
    assert (
        result == 9999
    ), f"Expected 9999 for scalable/48x48 path (scalable takes precedence), got {result}."


def test_parse_size_valid_nxn_returns_n():
    """Preservation: a path with a clean 'NxN' component and no earlier x-containing
    component returns N.

    The path /Adwaita/48x48/ has no earlier component with 'x', so the parser
    hits '48x48', splits on 'x', '48'.isdigit() is True, returns 48.
    MUST PASS on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/48x48/apps/firefox.png")
    assert result == 48, f"Expected 48 for clean 48x48 path, got {result}."


def test_parse_size_16x16_returns_16():
    """Preservation: a path with a '16x16' component and no preceding x-component returns 16.

    Similar to 48x48 — the unfixed code handles clean NxN paths correctly as long as
    no earlier path component contains 'x'. MUST PASS on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/16x16/apps/something.png")
    assert result == 16, f"Expected 16 for 16x16 path, got {result}."


def test_parse_size_pure_digit_returns_value():
    """Preservation: a path component that is purely a digit (e.g. '48') returns that value.

    The elif p.isdigit() branch handles directory names that are plain integers.
    Observed on unfixed code: returns 48 for '.../48/apps/...'. MUST PASS on unfixed code.
    """
    result = IconResolver._parse_size("/usr/share/icons/Adwaita/48/apps/something.png")
    assert result == 48, f"Expected 48 for pure-digit path component '48', got {result}."


# Small concrete set of paths covering both scalable and clean NxN cases.
# All paths avoid the bug trigger (no component like '2x-retina' preceding
# the NxN component).
_SIZE_PARSE_CASES = [
    ("/usr/share/icons/Adwaita/scalable/apps/firefox.svg", 9999),
    ("/usr/share/icons/hicolor/scalable/apps/app.svg", 9999),
    ("/usr/share/icons/Adwaita/scalable/48x48/apps/firefox.svg", 9999),
    ("/usr/share/icons/Adwaita/48x48/apps/firefox.png", 48),
    ("/usr/share/icons/Adwaita/16x16/apps/something.png", 16),
    ("/usr/share/icons/hicolor/32x32/apps/thing.png", 32),
    ("/usr/share/icons/Adwaita/48/apps/something.png", 48),
]


@settings(max_examples=len(_SIZE_PARSE_CASES))
@given(st.sampled_from(_SIZE_PARSE_CASES))
def test_pbt_parse_size_scalable_and_clean_nxn(path_expected):
    """Property: for paths that contain 'scalable' or a clean NxN component (no preceding
    x-containing components), _parse_size returns the expected value.

    Uses a concrete set of paths that avoid the '2x-retina' bug trigger.
    MUST PASS on unfixed code.
    """
    path, expected = path_expected
    result = IconResolver._parse_size(path)
    assert result == expected, f"_parse_size({path!r}): expected {expected}, got {result}."


# ── Task 12: Cache re-validation tests ───────────────────────────────────────


def test_resolve_stale_cached_path_evicts_and_resolves():
    """Task 12: resolve() evicts a stale cached path and re-resolves via _find.

    Prime the cache with a path that no longer exists on disk. resolve() should
    detect the stale entry, call _find() to get a fresh result, update the cache,
    and return the new path.
    """

    resolver = IconResolver()
    new_path = "/some/valid/replacement/firefox.png"

    # Prime cache with a stale (non-existent) path
    resolver._cache["firefox"] = "/nonexistent/old/firefox.png"

    # _find() will be called because the cached path no longer exists
    with __import__("unittest.mock", fromlist=["patch"]).patch.object(
        resolver, "_find", return_value=new_path
    ) as mock_find:
        result = resolver.resolve("firefox")

    assert result == new_path, f"Expected re-resolved path {new_path!r}, got {result!r}."
    assert (
        resolver._cache["firefox"] == new_path
    ), f"Cache should be updated to {new_path!r}, got {resolver._cache['firefox']!r}."
    mock_find.assert_called_once_with("firefox")


def test_resolve_valid_cached_path_returns_cached():
    """Task 12: resolve() returns a cached path without calling _find when it still exists.

    Prime the cache with a path that exists on disk. resolve() should return the
    cached value immediately without re-resolving.
    """
    import os
    import tempfile
    from unittest.mock import patch

    resolver = IconResolver()

    # Use a real file so os.path.exists() returns True
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        existing_path = f.name

    try:
        resolver._cache["myapp"] = existing_path

        with patch.object(resolver, "_find") as mock_find:
            result = resolver.resolve("myapp")

        assert result == existing_path, f"Expected cached path {existing_path!r}, got {result!r}."
        mock_find.assert_not_called()
    finally:
        os.unlink(existing_path)
