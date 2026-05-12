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

"""
UI settings loaded from ~/.config/linxpad/settings.conf

Example:
    # App grid configuration
    rows=3
    cols=8
    # font size for app icon labels (points)
    font-size=14
    # Transparency: 0 = completely transparent, 100 = no transparency
    transparency=95
    # Launch mode: window or full-screen
    launch-as=full-screen
    # Keep search/folder state when re-opening: yes or no
    keep-previous-state=yes
"""

import logging
import os

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.expanduser("~/.config/linxpad/settings.conf")

_DEFAULTS = {
    "cols": "8",
    "rows": "3",
    "spacing": "10",
    "font-size": "14",
    "transparency": "95",
    "launch-as": "full-screen",
    "keep-previous-state": "yes",
}

_VALID = {
    "launch-as": {"window", "full-screen"},
    "keep-previous-state": {"yes", "no"},
}


class UISettings:
    def __init__(self, path: str = SETTINGS_FILE):
        self._path = path
        self._values = dict(_DEFAULTS)
        self._load()

    # ── public properties ────────────────────────────────────────────────────

    @property
    def cols(self) -> int:
        try:
            return max(1, min(16, int(self._values["cols"])))
        except ValueError:
            return int(_DEFAULTS["cols"])

    @property
    def rows(self) -> int:
        try:
            return max(1, min(10, int(self._values["rows"])))
        except ValueError:
            return int(_DEFAULTS["rows"])

    @property
    def spacing(self) -> int:
        try:
            return max(0, min(60, int(self._values["spacing"])))
        except ValueError:
            return int(_DEFAULTS["spacing"])

    @property
    def font_size(self) -> int:
        try:
            return max(8, min(32, int(self._values["font-size"])))
        except ValueError:
            return int(_DEFAULTS["font-size"])

    @property
    def opacity(self) -> float:
        """Window opacity as 0.0–1.0 (transparency setting is 0–100)."""
        try:
            t = max(0, min(100, int(self._values["transparency"])))
        except ValueError:
            t = int(_DEFAULTS["transparency"])
        return t / 100.0

    @property
    def keep_previous_state(self) -> bool:
        return self._values["keep-previous-state"] == "yes"

    @property
    def fullscreen(self) -> bool:
        return self._values["launch-as"] == "full-screen"

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(self._path):
            self._write_defaults()
            return
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key not in _DEFAULTS:
                        continue
                    allowed = _VALID.get(key)
                    if allowed and value not in allowed:
                        logger.warning("Invalid value %r for %r, using default", value, key)
                        continue
                    self._values[key] = value
        except Exception:
            logger.exception("Failed to load settings from %s", self._path)

    def save(self) -> None:
        """Write current _values to the settings file."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w") as f:
                f.write(
                    "# Full Screen Launcher \u2014 UI settings\n"
                    "\n"
                    "# App grid configuration\n"
                    f"rows={self._values['rows']}\n"
                    f"cols={self._values['cols']}\n"
                    "\n"
                    "# Grid spacing between icons (pixels)\n"
                    f"spacing={self._values['spacing']}\n"
                    "\n"
                    "# Font size for app icon labels (points, 8\u201332)\n"
                    f"font-size={self._values['font-size']}\n"
                    "\n"
                    "# Transparency: 0 = completely transparent, 100 = no transparency\n"
                    f"transparency={self._values['transparency']}\n"
                    "\n"
                    "# Launch mode: window or full-screen\n"
                    f"launch-as={self._values['launch-as']}\n"
                    "\n"
                    "# Keep search/folder state when re-opening: yes or no\n"
                    f"keep-previous-state={self._values['keep-previous-state']}\n"
                )
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self._path)
        except Exception:
            logger.exception("Failed to save settings to %s", self._path)

    def _write_defaults(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w") as f:
                f.write(
                    "# Full Screen Launcher — UI settings\n"
                    "\n"
                    "# App grid configuration\n"
                    "rows=3\n"
                    "cols=8\n"
                    "\n"
                    "# Grid spacing between icons (pixels)\n"
                    "spacing=10\n"
                    "\n"
                    "# Font size for app icon labels (points, 8–32)\n"
                    "font-size=14\n"
                    "\n"
                    "# Transparency: 0 = completely transparent, 100 = no transparency\n"
                    "transparency=95\n"
                    "\n"
                    "# Launch mode: window or full-screen\n"
                    "launch-as=full-screen\n"
                    "\n"
                    "# Keep search/folder state when re-opening: yes or no\n"
                    "keep-previous-state=yes\n"
                )
        except Exception:
            logger.exception("Failed to write default settings to %s", self._path)
