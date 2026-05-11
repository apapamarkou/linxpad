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
 
import os
from urllib.parse import urlparse

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QLabel

from ..theme import ROW_DESC, ROW_LINK, ROW_NAME, ROW_PATH, ROW_URL
from .base_row import BaseRow


class FileRow(BaseRow):
    def __init__(self, item: dict, on_click):
        super().__init__(height=56, on_click=on_click)
        theme_name = "folder" if item["is_dir"] else "text-x-generic"
        qicon = QIcon.fromTheme(theme_name)
        if not qicon.isNull():
            self.icon_label.setPixmap(qicon.pixmap(self.ICON_SIZE, self.ICON_SIZE))
        else:
            self.icon_label.setText("📁" if item["is_dir"] else "📄")
            self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")

        self.add_primary(item["name"], ROW_NAME)
        rel = item["path"].replace(os.path.expanduser("~"), "~", 1)
        self.add_secondary(rel, ROW_PATH)


class WebSearchRow(BaseRow):
    def __init__(self, query: str, on_click):
        super().__init__(height=56, on_click=on_click)
        qicon = QIcon.fromTheme("web-browser")
        if not qicon.isNull():
            self.icon_label.setPixmap(qicon.pixmap(self.ICON_SIZE, self.ICON_SIZE))
        else:
            self.icon_label.setText("🌐")
            self.icon_label.setStyleSheet("font-size: 20px; background: transparent;")

        self.add_primary(f'Search for "{query}"', ROW_NAME)
        self.add_secondary(f"https://www.google.com/search?q={query.replace(' ', '+')}", ROW_URL)


class WebResultRow(BaseRow):
    def __init__(self, result: dict, on_click):
        # WebResultRow has no icon — override layout margins to match original
        super().__init__(height=0, on_click=on_click)
        self._layout.setContentsMargins(52, 4, 12, 4)
        self._layout.setSpacing(0)
        # Remove the icon label added by BaseRow
        self._layout.removeWidget(self.icon_label)
        self.icon_label.hide()

        title = QLabel(result["title"])
        title.setStyleSheet(ROW_LINK)
        title.setWordWrap(True)
        self._text_layout.addWidget(title)

        base_url = result.get("base") or urlparse(result["url"]).netloc or result["url"]
        self._text_layout.addWidget(QLabel(base_url))
        self._text_layout.itemAt(self._text_layout.count() - 1).widget().setStyleSheet(ROW_URL)

        if result.get("description"):
            desc = QLabel(result["description"])
            desc.setStyleSheet(ROW_DESC)
            desc.setWordWrap(True)
            self._text_layout.addWidget(desc)
