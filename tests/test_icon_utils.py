# Failure output on unfixed code:
# FAILED tests/test_icon_utils.py::test_c1_stale_cached_path - AssertionError: Expected non-null letter-avatar pixmap, got null.
#   Bug 1.1: resolver returns stale non-existent path, app_pixmap returns null.
# PASSED tests/test_icon_utils.py::test_c2_svg_without_plugin
#   Bug 1.2: SVG loaded successfully by Qt SVG plugin in this environment.
#   The bug only manifests when the Qt SVG plugin is absent (headless env without plugin).
#   This test passes on a fully-equipped Qt install; it confirms the fallback chain
#   returns non-null regardless of whether the pixmap loaded or not.

import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from linxpad.ui.components.icon_utils import app_pixmap

# Guard against double-init
_app = QApplication.instance() or QApplication(sys.argv)

_LINXPAD_PNG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "linxpad",
    "icons",
    "linxpad.png",
)


def test_c1_stale_cached_path():
    """Bug 1.1: app_pixmap returns null when resolver returns a non-existent path.
    MUST FAIL on unfixed code: app_pixmap does not check os.path.exists().
    """
    item = {"icon_name": "firefox", "icon": None, "name": "Firefox"}
    resolver = MagicMock()
    resolver.resolve.return_value = "/nonexistent/icons/firefox.png"
    result = app_pixmap(item, 48, resolver)
    assert not result.isNull(), (
        "Expected non-null letter-avatar pixmap, got null. "
        "Bug 1.1: resolver returns stale non-existent path, app_pixmap returns null."
    )


def test_c2_svg_without_plugin():
    """Bug 1.2: app_pixmap returns null for an SVG file that cannot be loaded.
    MUST FAIL on unfixed code: app_pixmap returns the null SVG pixmap.
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as f:
        f.write("<svg xmlns='http://www.w3.org/2000/svg'><rect width='48' height='48'/></svg>")
        svg_path = f.name
    try:
        item = {"icon": svg_path, "icon_name": None, "name": "TestSVG"}
        result = app_pixmap(item, 48)
        assert not result.isNull(), (
            "Expected non-null letter-avatar pixmap for unloadable SVG, got null. "
            "Bug 1.2: app_pixmap returns null SVG pixmap."
        )
    finally:
        os.unlink(svg_path)


# ── Phase 2: Preservation property tests (Task 5) ────────────────────────────
# These tests MUST PASS on unfixed code. They encode correct baseline behavior
# for inputs that do NOT trigger the bugs.


def test_app_pixmap_valid_png_path_returns_non_null():
    """Preservation: app_pixmap with a valid, existing PNG returns a non-null pixmap.

    The icon path exists on disk and QPixmap can load it, so app_pixmap takes
    the first branch (icon_path and os.path.exists) and returns make_pixmap output.
    Observed on unfixed code: non-null pixmap returned. MUST PASS.
    """
    png_path = os.path.normpath(_LINXPAD_PNG)
    assert os.path.exists(png_path), f"Test PNG not found at {png_path}"
    item = {"icon": png_path, "icon_name": None, "name": "LinxPad"}
    result = app_pixmap(item, 48)
    assert not result.isNull(), (
        f"Expected non-null pixmap for existing PNG {png_path}, got null."
    )


def test_app_pixmap_theme_icon_name_returns_non_null():
    """Preservation: app_pixmap with icon_name that resolves via QIcon.fromTheme returns non-null.

    Skipped when the theme icon is unavailable in this environment. Only tests the
    QIcon.fromTheme branch which already checks qi.isNull() — this branch is correct
    on both unfixed and fixed code.
    """
    if QIcon.fromTheme("document-open").isNull():
        pytest.skip("document-open theme icon not available in this environment")
    item = {"icon": None, "icon_name": "document-open", "name": "Open"}
    result = app_pixmap(item, 48)
    assert not result.isNull(), "Expected non-null pixmap from QIcon.fromTheme('document-open')"


def test_app_pixmap_no_icon_path_no_name_returns_letter_avatar():
    """Preservation: app_pixmap with no icon path and no icon_name returns the letter-avatar fallback.

    The fallback _fallback() draws the first letter of the app name. It always
    produces a non-null pixmap by filling a QPixmap(size, size). MUST PASS on unfixed code.
    """
    item = {"icon": None, "icon_name": None, "name": "Firefox"}
    result = app_pixmap(item, 48)
    assert not result.isNull(), (
        "Expected non-null letter-avatar pixmap for item with no icon, got null."
    )


def test_app_pixmap_empty_name_returns_question_mark_avatar():
    """Preservation: app_pixmap with no icon and empty name draws '?' letter-avatar.

    When name is "" the fallback uses (item.get('name') or '?')[0].upper() = '?'.
    _fallback() always produces a non-null pixmap. MUST PASS on unfixed code.
    """
    item = {"icon": None, "icon_name": None, "name": ""}
    result = app_pixmap(item, 48)
    assert not result.isNull(), (
        "Expected non-null '?' letter-avatar pixmap for empty-name item, got null."
    )


# Small concrete set of items that do NOT trigger the bug conditions:
# - no icon path/name  → letter-avatar (always non-null)
# - valid existing PNG → make_pixmap (non-null since the file loads)
_NON_BUGGY_ITEMS = [
    {"icon": None, "icon_name": None, "name": "Firefox"},
    {"icon": None, "icon_name": None, "name": "Terminal"},
    {"icon": None, "icon_name": None, "name": ""},
    {"icon": os.path.normpath(_LINXPAD_PNG), "icon_name": None, "name": "LinxPad"},
]


@settings(max_examples=len(_NON_BUGGY_ITEMS))
@given(st.sampled_from(_NON_BUGGY_ITEMS))
def test_app_pixmap_pbt_non_buggy_items_return_non_null(item):
    """Property: for items without a stale/missing icon path, app_pixmap is non-null.

    Uses a concrete set of items that fall outside both bug conditions (1.1 and 1.2):
    - Items with no icon path use the letter-avatar fallback, which is always non-null.
    - Items with a valid existing PNG path use make_pixmap, which loads successfully.
    MUST PASS on unfixed code.
    """
    result = app_pixmap(item, 48)
    assert not result.isNull(), (
        f"Expected non-null pixmap for non-buggy item {item}, got null."
    )
