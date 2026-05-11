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
 
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..theme import ROW_NORMAL


class BaseRow(QWidget):
    """Shared row layout: icon + two-line text, hover effect, click → on_click()."""

    ICON_SIZE = 40

    def __init__(self, height: int, on_click=None):
        super().__init__()
        self._on_click = on_click
        if height:
            self.setFixedHeight(height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(ROW_NORMAL)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(16)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.icon_label)

        self._text_layout = QVBoxLayout()
        self._text_layout.setSpacing(2)
        self._text_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._text_layout)
        self._layout.addStretch()

    def add_primary(self, text: str, style: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(style)
        self._text_layout.addWidget(label)
        return label

    def add_secondary(self, text: str, style: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(style)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._text_layout.addWidget(label)
        return label

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click()
