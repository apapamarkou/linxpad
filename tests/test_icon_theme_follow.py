# Icon-theme-follow bugfix — exploration and preservation property tests
#
# Task 1: Bug condition exploration test
#   Asserts the EXPECTED (fixed) behavior: when detected_theme="papirus" is used
#   the resolver returns a path under papirus/.
#   On UNFIXED code (no detected_theme arg) this test FAILS, confirming the bug.
#
# Task 2: Preservation property tests
#   Written and run on UNFIXED code — all must PASS, encoding baseline behavior.

import os
import tempfile
import textwrap
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import linxpad.services.icons as icons_module
from linxpad.services.icons import IconResolver, detect_icon_theme

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_icon_tree(base: str, entries: list[tuple[str, ...]]) -> None:
    """Create empty SVG stub files at the given sub-paths under *base*."""
    for parts in entries:
        path = os.path.join(base, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("<svg/>")


# ---------------------------------------------------------------------------
# Task 1 — Bug condition exploration (Property 1)
#
# Validates: Requirements 1.1, 1.3
#
# The property encodes EXPECTED behavior: given a fake tree containing both a
# papirus icon and a breeze icon for the same name, IconResolver with
# detected_theme="papirus" MUST return the papirus path.
#
# On UNFIXED code (no detected_theme param → Breeze gets score 3, Papirus gets
# score 0) the assertion `"/papirus/" in result` FAILS, proving the bug.
# After the fix is applied, the test PASSES.
# ---------------------------------------------------------------------------

# Valid icon-name characters: alphanumeric, hyphens, underscores, dots.
# Keep names short so they are valid filename stems without weird characters.
_icon_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=32,
).filter(lambda s: s.strip("-_") != "")


@settings(max_examples=50)
@given(icon_name=_icon_name_strategy)
def test_pbt_bug_condition_user_theme_beats_breeze(icon_name: str) -> None:
    """Property 1 (Bug Condition): detected_theme="papirus" → papirus path returned.

    Validates: Requirements 2.1, 2.3

    For every generated icon name, both a papirus and a breeze copy exist at the
    same size (48x48). With detected_theme="papirus", the resolver MUST return a
    path whose string contains "/papirus/".

    On UNFIXED code (IconResolver() with no detected_theme) this assertion FAILS
    because Breeze wins (score 3 vs score 0 for Papirus). That failure IS the
    expected outcome for Task 1 — it confirms the bug exists.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _make_icon_tree(tmp, [
            ("papirus", "apps", "48x48", f"{icon_name}.svg"),
            ("breeze",  "apps", "48x48", f"{icon_name}.svg"),
        ])

        original_paths = icons_module._SEARCH_PATHS
        icons_module._SEARCH_PATHS = [tmp]
        try:
            # Fixed call uses detected_theme="papirus":
            resolver = IconResolver(detected_theme="papirus")
            result = resolver.resolve(icon_name)
        finally:
            icons_module._SEARCH_PATHS = original_paths

        assert result is not None, (
            f"resolve({icon_name!r}) returned None — expected a papirus path."
        )
        assert "/papirus/" in result, (
            f"resolve({icon_name!r}) returned {result!r}; "
            "expected a path under /papirus/ but got a path from a different theme. "
            "This failure on UNFIXED code confirms the bug: Breeze beats the user's theme."
        )


# ---------------------------------------------------------------------------
# Task 2 — Preservation property tests (run on UNFIXED code)
#
# All tests in this section MUST PASS on unfixed code.
# They encode the baseline behavior that the fix must not break.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 2a. Breeze beats hicolor at the same size
#
# Validates: Requirements 3.4, 3.5
# ---------------------------------------------------------------------------

def test_pbt_preservation_breeze_beats_hicolor() -> None:
    """Preservation: when both breeze and hicolor have the same-size icon, breeze wins.

    Validates: Requirements 3.4, 3.5
    """
    with tempfile.TemporaryDirectory() as tmp:
        _make_icon_tree(tmp, [
            ("breeze", "apps", "48x48", "folder.svg"),
            ("hicolor", "apps", "48x48", "folder.svg"),
        ])

        original_paths = icons_module._SEARCH_PATHS
        icons_module._SEARCH_PATHS = [tmp]
        try:
            resolver = IconResolver()
            result = resolver.resolve("folder")
        finally:
            icons_module._SEARCH_PATHS = original_paths

        assert result is not None, "resolve('folder') returned None — expected a breeze path."
        assert "/breeze/" in result, (
            f"resolve('folder') returned {result!r}; expected a path under /breeze/ "
            "but got something else. Breeze (score 3) must beat hicolor (score 2)."
        )


# ---------------------------------------------------------------------------
# 2b. Cache hit — second resolve() does not re-walk the filesystem
#
# Validates: Requirements 3.6
# ---------------------------------------------------------------------------

def test_pbt_preservation_cache_hit() -> None:
    """Preservation: second resolve() for the same name is served from cache.

    Validates: Requirements 3.6

    Monkeypatches os.walk to count how many times it is called. The first
    resolve() populates the cache; the second must not trigger another walk.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _make_icon_tree(tmp, [
            ("breeze", "apps", "48x48", "terminal.svg"),
        ])

        walk_call_count = []
        original_walk = os.walk
        original_paths = icons_module._SEARCH_PATHS

        def counting_walk(path, *args, **kwargs):
            walk_call_count.append(path)
            yield from original_walk(path, *args, **kwargs)

        icons_module._SEARCH_PATHS = [tmp]
        try:
            resolver = IconResolver()
            with patch("linxpad.services.icons.os.walk", side_effect=counting_walk):
                result1 = resolver.resolve("terminal")
                calls_after_first = len(walk_call_count)
                result2 = resolver.resolve("terminal")
                calls_after_second = len(walk_call_count)
        finally:
            icons_module._SEARCH_PATHS = original_paths

        assert result1 == result2, (
            f"First resolve returned {result1!r}, second returned {result2!r} — cache must return same value."
        )
        assert calls_after_first > 0, "os.walk was never called — first resolve should have walked."
        assert calls_after_second == calls_after_first, (
            f"os.walk was called {calls_after_second - calls_after_first} extra time(s) on the second "
            "resolve — expected 0 (cache hit)."
        )


# ---------------------------------------------------------------------------
# 2c. Unknown icon name returns None
#
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------

@settings(max_examples=30)
@given(icon_name=_icon_name_strategy)
def test_pbt_preservation_unknown_icon_returns_none(icon_name: str) -> None:
    """Preservation: resolve() returns None when no matching icon exists.

    Validates: Requirements 3.3

    Uses an empty temporary directory so no icons are present for any name.
    """
    with tempfile.TemporaryDirectory() as tmp:
        original_paths = icons_module._SEARCH_PATHS
        icons_module._SEARCH_PATHS = [tmp]
        try:
            resolver = IconResolver()
            result = resolver.resolve(icon_name)
        finally:
            icons_module._SEARCH_PATHS = original_paths

        assert result is None, (
            f"resolve({icon_name!r}) returned {result!r}; expected None when the icon "
            "is absent from all search paths."
        )


# ---------------------------------------------------------------------------
# 2d. Absolute path is returned as-is
#
# Validates: Requirements 3.1, 3.2
# ---------------------------------------------------------------------------

def test_pbt_preservation_absolute_path_returned_as_is() -> None:
    """Preservation: an existing absolute path is returned unchanged.

    Validates: Requirements 3.1, 3.2

    Creates a real file at an absolute path and passes that path directly to
    resolve(). The resolver must return the same path without modification.
    """
    with tempfile.TemporaryDirectory() as tmp:
        icon_path = os.path.join(tmp, "my_custom_icon.png")
        with open(icon_path, "wb") as fh:
            # Minimal 1×1 white PNG
            fh.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
                b"\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc"
                b"\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
            )

        resolver = IconResolver()
        result = resolver.resolve(icon_path)

        assert result == icon_path, (
            f"resolve({icon_path!r}) returned {result!r}; "
            "expected the same absolute path to be returned unchanged."
        )


# ---------------------------------------------------------------------------
# 2e. Property: detected_theme=None matches the no-arg constructor
#
# Validates: Requirements 3.4, 3.5
#
# NOTE: IconResolver.__init__ does NOT yet accept detected_theme on unfixed
# code. This test is marked xfail so it "passes" (as an expected failure) now
# and flips to a real PASS once the fix is applied.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="detected_theme param not yet implemented in IconResolver.__init__",
    strict=False,
)
@settings(max_examples=30)
@given(icon_name=_icon_name_strategy)
def test_pbt_preservation_detected_theme_none_matches_no_arg(icon_name: str) -> None:
    """Preservation: IconResolver(detected_theme=None) equals IconResolver() on a Breeze-only tree.

    Validates: Requirements 3.4, 3.5

    On a fake tree containing only Breeze icons, both constructors must resolve
    each icon name to the same path (or both None). This guards against the fix
    accidentally changing behavior when no theme is detected.
    """
    with tempfile.TemporaryDirectory() as tmp:
        _make_icon_tree(tmp, [
            ("breeze", "apps", "48x48", f"{icon_name}.svg"),
        ])

        original_paths = icons_module._SEARCH_PATHS
        icons_module._SEARCH_PATHS = [tmp]
        try:
            result_no_arg = IconResolver().resolve(icon_name)
            result_none = IconResolver(detected_theme=None).resolve(icon_name)
        finally:
            icons_module._SEARCH_PATHS = original_paths

        assert result_no_arg == result_none, (
            f"IconResolver().resolve({icon_name!r}) = {result_no_arg!r} but "
            f"IconResolver(detected_theme=None).resolve({icon_name!r}) = {result_none!r}. "
            "They must be identical when detected_theme=None."
        )


# ---------------------------------------------------------------------------
# Task 3.1 — Unit tests for detect_icon_theme()
# ---------------------------------------------------------------------------


def test_detect_icon_theme_kde(tmp_path):
    """KDE: reads [Icons] Theme from kdeglobals."""
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[Icons]\nTheme=Papirus\n")
    result = detect_icon_theme(_kdeglobals=str(kdeglobals))
    assert result == "Papirus"


def test_detect_icon_theme_kde_missing_section(tmp_path):
    """KDE: file exists but [Icons] section is absent → falls through to None."""
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[General]\nColorScheme=Breeze\n")
    # Patch subprocess.run so gsettings does not pick up the real desktop theme.
    with patch("linxpad.services.icons.subprocess.run", side_effect=FileNotFoundError):
        result = detect_icon_theme(
            _kdeglobals=str(kdeglobals),
            _xfce_xml=str(tmp_path / "nonexistent.xml"),
            _lxsession_glob=str(tmp_path / "nomatch" / "*.conf"),
        )
    assert result is None


def test_detect_icon_theme_xfce(tmp_path):
    """XFCE: reads IconThemeName from xsettings.xml."""
    xfce_xml = tmp_path / "xsettings.xml"
    xfce_xml.write_text(textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <channel name="xsettings" version="1.0">
          <property name="Net" type="empty">
            <property name="IconThemeName" type="string" value="Adwaita"/>
          </property>
        </channel>
    """))
    result = detect_icon_theme(
        _kdeglobals=str(tmp_path / "nonexistent"),
        _xfce_xml=str(xfce_xml),
    )
    assert result == "Adwaita"


def test_detect_icon_theme_xfce_malformed_xml(tmp_path):
    """XFCE: malformed XML is silenced, falls through to None."""
    xfce_xml = tmp_path / "xsettings.xml"
    xfce_xml.write_text("<<<not xml>>>")
    with patch("linxpad.services.icons.subprocess.run", side_effect=FileNotFoundError):
        result = detect_icon_theme(
            _kdeglobals=str(tmp_path / "nonexistent"),
            _xfce_xml=str(xfce_xml),
            _lxsession_glob=str(tmp_path / "nomatch" / "*.conf"),
        )
    assert result is None


def test_detect_icon_theme_lxde(tmp_path):
    """LXDE: reads sNet/IconThemeName from desktop.conf via glob."""
    session_dir = tmp_path / "LXDE"
    session_dir.mkdir()
    conf = session_dir / "desktop.conf"
    conf.write_text("[GTK]\nsNet/IconThemeName=Mint-Y\n")
    # Pass a glob that matches the file we just wrote
    result = detect_icon_theme(
        _kdeglobals=str(tmp_path / "nonexistent"),
        _xfce_xml=str(tmp_path / "nonexistent.xml"),
        _lxsession_glob=str(tmp_path / "LXDE" / "desktop.conf"),
    )
    assert result == "Mint-Y"


def test_detect_icon_theme_none_fallback(tmp_path):
    """No config files present and gsettings unavailable → returns None."""
    with patch("linxpad.services.icons.subprocess.run", side_effect=FileNotFoundError):
        result = detect_icon_theme(
            _kdeglobals=str(tmp_path / "nonexistent"),
            _xfce_xml=str(tmp_path / "nonexistent.xml"),
            _lxsession_glob=str(tmp_path / "nomatch" / "*.conf"),
        )
    assert result is None
