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

from dataclasses import dataclass, field


@dataclass
class Folder:
    id: str
    name: str
    app_ids: list[str] = field(default_factory=list)
    sort_id: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "appIds": self.app_ids,
            "sortId": self.sort_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Folder":
        return cls(
            id=d["id"],
            name=d["name"],
            app_ids=d.get("appIds", []),
            sort_id=d.get("sortId", 0),
        )
