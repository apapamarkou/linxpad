import logging
import os

from .icons import IconResolver

logger = logging.getLogger(__name__)

_DESKTOP_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]


class DesktopScanner:
    def __init__(self, icon_resolver: IconResolver | None = None):
        self._icons = icon_resolver or IconResolver()

    def scan(self) -> list[dict]:
        """Return list of app_info dicts from all .desktop files."""
        found, seen = [], set()
        for d in _DESKTOP_DIRS:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    if not fname.endswith(".desktop"):
                        continue
                    info = self._parse(os.path.join(d, fname))
                    if info:
                        key = (info["name"], info["exec"])
                        if key not in seen:
                            found.append(info)
                            seen.add(key)
            except PermissionError:
                logger.warning("Permission denied: %s", d)
        return found

    def _parse(self, filepath: str) -> dict | None:
        try:
            name = exec_cmd = icon = comment = None
            no_display = False
            in_desktop_entry = False

            with open(filepath, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line == "[Desktop Entry]":
                        in_desktop_entry = True
                        continue
                    if line.startswith("[") and line != "[Desktop Entry]":
                        if in_desktop_entry:
                            break
                        continue
                    if not in_desktop_entry or not line or line.startswith("#") or "=" not in line:
                        continue

                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()

                    if key == "Name" and not name:
                        name = value
                    elif key == "Exec" and not exec_cmd:
                        exec_cmd = value
                    elif key == "Icon" and not icon:
                        icon = value
                    elif key == "Comment" and not comment:
                        comment = value
                    elif key == "NoDisplay":
                        no_display = value.lower() in ("true", "1", "yes")
                    elif key == "Type" and value != "Application":
                        return None

            if name and exec_cmd and not no_display:
                return {
                    "name": name,
                    "exec": os.path.basename(filepath),
                    "icon": self._icons.resolve(icon),
                    "icon_name": icon,
                    "comment": comment,
                }
        except Exception:
            logger.debug("Failed to parse %s", filepath, exc_info=True)
        return None
