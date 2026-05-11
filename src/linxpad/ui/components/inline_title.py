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
 
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QLabel, QLineEdit, QSizePolicy, QStackedWidget

from ..theme import TITLE_EDIT, TITLE_LABEL


class InlineTitle(QStackedWidget):
    """Folder title that switches between a label and an inline editor on click."""

    _DEFAULT_NAME = "App Folder"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_commit = None

        self._label = QLabel()
        self._label.setStyleSheet(TITLE_LABEL)
        self._label.setCursor(Qt.CursorShape.IBeamCursor)

        self._edit = QLineEdit()
        self._edit.setStyleSheet(TITLE_EDIT)
        self._edit.setMaximumWidth(400)
        self._edit.returnPressed.connect(self._commit)
        self._edit.installEventFilter(self)

        self.addWidget(self._label)
        self.addWidget(self._edit)
        self.setCurrentWidget(self._label)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def start_edit(self, on_commit) -> None:
        self._on_commit = on_commit
        self._edit.setText(self._label.text())
        self._edit.selectAll()
        self.setCurrentWidget(self._edit)
        self._edit.setFocus()

    def _commit(self) -> None:
        name = self._edit.text().strip() or self._DEFAULT_NAME
        self._label.setText(name)
        self.setCurrentWidget(self._label)
        if self._on_commit:
            self._on_commit(name)

    def _cancel(self) -> None:
        self.setCurrentWidget(self._label)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._edit:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._commit()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._cancel()
                    return True
            elif event.type() == QEvent.Type.FocusOut:
                self._commit()
                return False
        return False

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
