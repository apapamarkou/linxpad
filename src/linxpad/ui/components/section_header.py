from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..theme import SECTION_HEADER


class SectionHeader(QWidget):
    def __init__(self, text: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 4)
        self._label = QLabel(text)
        self._label.setStyleSheet(SECTION_HEADER)
        layout.addWidget(self._label)
        layout.addStretch()

    def set_text(self, text: str) -> None:
        self._label.setText(text)
