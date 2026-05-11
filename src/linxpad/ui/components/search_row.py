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
 
from ..theme import ROW_NAME, ROW_SUB
from .base_row import BaseRow
from .icon_utils import load_app_icon


class SearchRow(BaseRow):
    def __init__(self, app: dict, on_click, icon_resolver=None):
        super().__init__(height=64, on_click=on_click)
        self._app = app
        load_app_icon(self.icon_label, app, self.ICON_SIZE, icon_resolver)
        self.add_primary(app["name"], ROW_NAME)
        comment = app.get("comment") or ""
        if comment:
            self.add_secondary(comment, ROW_SUB)

    def launch(self) -> None:
        if self._on_click:
            self._on_click()
