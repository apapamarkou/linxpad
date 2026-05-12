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

"""Dots indicator widget for page navigation."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..theme import DOT_ACTIVE, DOT_INACTIVE


class DotsIndicator(QWidget):
    page_requested = pyqtSignal(int)

    DOT_SIZE = 28
    DOT_SPACING = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots: list[QLabel] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(self.DOT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout = layout

    def set_count(self, count: int) -> None:
        for dot in self._dots:
            dot.setParent(None)
        self._dots = []
        for i in range(count):
            dot = QLabel()
            dot.setFixedSize(self.DOT_SIZE, self.DOT_SIZE)
            dot.setStyleSheet(DOT_INACTIVE)
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            dot.mousePressEvent = lambda _e, n=i: self.page_requested.emit(n)
            self._layout.addWidget(dot)
            self._dots.append(dot)
        self.setVisible(count > 1)

    def set_active(self, index: int) -> None:
        for i, dot in enumerate(self._dots):
            dot.setStyleSheet(DOT_ACTIVE if i == index else DOT_INACTIVE)
