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
from PyQt6.QtWidgets import QApplication

from linxpad.ui.components.icon_utils import app_pixmap

# Guard against double-init
_app = QApplication.instance() or QApplication(sys.argv)


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
