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
 
import logging
import os

logger = logging.getLogger(__name__)

_SEARCH_PATHS = [
    "/usr/share/icons",
    "/usr/share/pixmaps",
    os.path.expanduser("~/.local/share/icons"),
]
_THEME_PRIORITY = {"breeze-dark": 4, "breeze": 3, "hicolor": 2}
_VALID_EXTS = {".png", ".svg", ".svgz"}


class IconResolver:
    def __init__(self):
        self._cache: dict = {}

    def resolve(self, icon_name: str | None) -> str | None:
        if not icon_name:
            return None
        if icon_name in self._cache:
            return self._cache[icon_name]

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
                        (p for t, p in _THEME_PRIORITY.items() if f"/{t}/" in full), 0
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
                a = p.split("x")[0]
                if a.isdigit():
                    return int(a)
            elif p.isdigit():
                return int(p)
        return 0
