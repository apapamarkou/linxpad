import textwrap

import pytest

from linxpad.services.desktop import DesktopScanner
from linxpad.services.icons import IconResolver


@pytest.fixture
def scanner(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "linxpad.services.desktop._DESKTOP_DIRS",
        [str(tmp_path)],
    )
    return DesktopScanner(IconResolver())


def write_desktop(path, content):
    path.write_text(textwrap.dedent(content))


def test_parses_valid_desktop_file(scanner, tmp_path):
    write_desktop(
        tmp_path / "firefox.desktop",
        """
        [Desktop Entry]
        Type=Application
        Name=Firefox
        Exec=firefox %u
        Icon=firefox
    """,
    )
    results = scanner.scan()
    assert len(results) == 1
    assert results[0]["name"] == "Firefox"
    assert results[0]["exec"] == "firefox.desktop"
    assert results[0]["icon_name"] == "firefox"


def test_skips_nodisplay(scanner, tmp_path):
    write_desktop(
        tmp_path / "hidden.desktop",
        """
        [Desktop Entry]
        Type=Application
        Name=Hidden
        Exec=hidden
        Icon=hidden
        NoDisplay=true
    """,
    )
    assert scanner.scan() == []


def test_skips_non_application_type(scanner, tmp_path):
    write_desktop(
        tmp_path / "link.desktop",
        """
        [Desktop Entry]
        Type=Link
        Name=Link
        Exec=something
    """,
    )
    assert scanner.scan() == []


def test_deduplicates_across_dirs(tmp_path, monkeypatch):
    dir1 = tmp_path / "d1"
    dir2 = tmp_path / "d2"
    dir1.mkdir()
    dir2.mkdir()
    for d in (dir1, dir2):
        write_desktop(
            d / "app.desktop",
            """
            [Desktop Entry]
            Type=Application
            Name=MyApp
            Exec=myapp
            Icon=myapp
        """,
        )
    monkeypatch.setattr(
        "linxpad.services.desktop._DESKTOP_DIRS",
        [str(dir1), str(dir2)],
    )
    results = DesktopScanner(IconResolver()).scan()
    assert len(results) == 1
