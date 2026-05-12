#  _     _                            _s
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

from dataclasses import dataclass


@dataclass
class Application:
    id: str
    name: str
    exec: str
    icon: str | None = None
    icon_name: str | None = None
    folder_id: str | None = None
    sort_id: int = 0
    comment: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "exec": self.exec,
            "icon": self.icon,
            "icon_name": self.icon_name,
            "folderId": self.folder_id,
            "sortId": self.sort_id,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Application":
        return cls(
            id=d["id"],
            name=d["name"],
            exec=d["exec"],
            icon=d.get("icon"),
            icon_name=d.get("icon_name"),
            folder_id=d.get("folderId"),
            sort_id=d.get("sortId", 0),
            comment=d.get("comment"),
        )
