#  _     _                            _
# | |   (_)_ __ __  ___ __   __ _  __| |
# | |   | | '_ \\ \/ / '_ \ / _` |/ _` |
# | |___| | | | |>  <| |_) | (_| | (_| |
# |_____|_|_| |_/_/\_\ .__/ \__,_|\__,_|
#                    |_|
#
# Author: Andrianos Papamarkou
# Licence: GPL3
# https://github.com/apapamarkou/linxpad
# https://apapamarkou.github.io/linxpad/

import configparser
import glob
import logging
import os
import subprocess
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

_SEARCH_PATHS = [
    "/usr/share/icons",
    "/usr/share/pixmaps",
    os.path.expanduser("~/.local/share/icons"),
]
_THEME_PRIORITY = {"breeze-dark": 4, "breeze": 3, "hicolor": 2}
_VALID_EXTS = {".png", ".svg", ".svgz"}


def detect_icon_theme(
    _kdeglobals: str | None = None,
    _xfce_xml: str | None = None,
    _lxsession_glob: str | None = None,
) -> str | None:
    """Return the active icon theme name from the desktop environment, or None.

    Checks sources in order: KDE/Plasma, XFCE, LXDE/LXQt, GNOME/Cinnamon.
    Never raises; all failures are silenced and fall through to the next source.

    Optional keyword arguments allow callers to override the default config
    paths for testing:
        _kdeglobals       — path to kdeglobals (default: ~/.config/kdeglobals)
        _xfce_xml         — path to xsettings.xml
        _lxsession_glob   — glob pattern for LXDE desktop.conf files
    """
    # 1. KDE/Plasma
    kde_path = _kdeglobals or os.path.expanduser("~/.config/kdeglobals")
    if os.path.isfile(kde_path):
        try:
            cfg = configparser.ConfigParser(strict=False)
            cfg.read(kde_path)
            if cfg.has_section("Icons") and cfg.has_option("Icons", "Theme"):
                return cfg["Icons"]["Theme"].strip()
        except Exception:
            pass

    # 2. XFCE
    xfce_path = _xfce_xml or os.path.expanduser(
        "~/.config/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml"
    )
    if os.path.isfile(xfce_path):
        try:
            tree = ET.parse(xfce_path)
            node = tree.getroot().find("./property[@name='Net']/property[@name='IconThemeName']")
            if node is not None and "value" in node.attrib:
                return node.attrib["value"].strip()
        except ET.ParseError:
            pass
        except Exception:
            pass

    # 3. LXDE/LXQt
    lx_glob = _lxsession_glob or os.path.expanduser("~/.config/lxsession/*/desktop.conf")
    for conf_path in sorted(glob.glob(lx_glob)):
        try:
            cfg = configparser.ConfigParser(strict=False)
            cfg.read(conf_path)
            if cfg.has_section("GTK") and cfg.has_option("GTK", "sNet/IconThemeName"):
                return cfg["GTK"]["sNet/IconThemeName"].strip()
        except Exception:
            pass

    # 4. GNOME/Cinnamon
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip().strip("'\"")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


class IconResolver:
    def __init__(self, detected_theme: str | None = None):
        self._cache: dict = {}
        self._theme_priority = dict(_THEME_PRIORITY)
        if detected_theme is not None:
            self._theme_priority[detected_theme.lower()] = 5

    def resolve(self, icon_name: str | None) -> str | None:
        if not icon_name:
            return None
        if icon_name in self._cache:
            cached = self._cache[icon_name]
            if cached is None or os.path.exists(cached):
                return cached
            # Cached path no longer exists — evict and re-resolve

        result = self._find(icon_name)
        self._cache[icon_name] = result
        return result

    def _find(self, icon_name: str) -> str | None:
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            return icon_name

        candidates = []
        for base in _SEARCH_PATHS:
            if not os.path.isdir(base):
                continue
            for root, _, files in os.walk(base):
                for f in files:
                    stem, ext = os.path.splitext(f)
                    if stem != icon_name or ext.lower() not in _VALID_EXTS:
                        continue
                    full = os.path.join(root, f)
                    theme_score = next(
                        (p for t, p in self._theme_priority.items() if f"/{t}/" in full), 0
                    )
                    size = self._parse_size(full)
                    candidates.append((size, theme_score, full))

        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    @staticmethod
    def _parse_size(path: str) -> int:
        parts = path.split(os.sep)
        if "scalable" in parts:
            return 9999
        for p in parts:
            if "x" in p:
                halves = p.split("x")
                if (
                    len(halves) == 2
                    and halves[0].isdigit()
                    and halves[1].isdigit()
                    and int(halves[0]) == int(halves[1])
                ):
                    return int(halves[0])
            elif p.isdigit():
                return int(p)
        return 0
