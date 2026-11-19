# Failure output on unfixed code:
# FAILED tests/test_icons.py::test_c5_size_misparse_retina_dir
#   AssertionError: Expected 0 for path with '2x-retina' dir (no NxN component), got 2.
#   Bug 1.5: _parse_size misparses '2x-retina' as size 2.
# FAILED tests/test_icons.py::test_c5_size_parse_valid_nxn
#   AssertionError: Expected 48 for path with '48x48' dir, got 2.
#   Bug 1.5: Parser returns early with 2 (from '2x-retina') before reaching '48x48'.
#   This companion test also FAILS on unfixed code — the bug is broader than expected:
#   not only does '2x-retina' misparse, it also shadows any valid NxN component later in the path.

import pytest

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
