import json
import logging
import os

from ..models import Application, Folder

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.expanduser("~/.config/linxpad")
CONFIG_FILE = os.path.join(CONFIG_DIR, "apps.json")


class ConfigService:
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

    def load(self) -> tuple[dict[str, Application], dict[str, Folder]]:
        if not os.path.exists(self.config_file):
            return {}, {}
        try:
            with open(self.config_file) as f:
                raw = json.load(f)
            apps = {k: Application.from_dict(v) for k, v in raw.get("applications", {}).items()}
            folders = {k: Folder.from_dict(v) for k, v in raw.get("folders", {}).items()}
            return apps, folders
        except Exception:
            logger.exception("Failed to load config")
            return {}, {}

    def save(self, apps: dict[str, Application], folders: dict[str, Folder]) -> None:
        tmp = self.config_file + ".tmp"
        try:
            data = {
                "applications": {k: v.to_dict() for k, v in apps.items()},
                "folders": {k: v.to_dict() for k, v in folders.items()},
            }
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.config_file)
        except Exception:
            logger.exception("Failed to save config")

    def is_empty(self) -> bool:
        return not os.path.exists(self.config_file)
