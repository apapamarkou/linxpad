"""IconItem — a QGraphicsWidget representing one app or folder icon.

Responsibilities:
- Render icon pixmap + name label
- Paint selection / hover / drop-target / ghost states
- Emit signals for click and drag start
- No knowledge of pages, grid layout, or drag logic
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSizeF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsWidget, QStyleOptionGraphicsItem, QWidget

from ..components.icon_utils import app_pixmap, folder_pixmap
from ..theme import (
    C_DROP_TARGET_BG,
    C_DROP_TARGET_BORDER,
    C_FOLDER_BG,
    C_FOLDER_BORDER,
    C_FOLDER_HOVER,
    C_GHOST_BG,
    C_NORMAL_HOVER,
    C_SELECTED_BG,
    C_SELECTED_BORDER,
    C_SELECTED_HOVER,
)

_LABEL_COLOR = QColor("#ffffff")
_LABEL_COLOR_DIM = QColor(255, 255, 255, 160)
_TRANSPARENT = QColor(0, 0, 0, 0)


class IconItem(QGraphicsWidget):
    """A single icon cell in the grid scene."""

    clicked = pyqtSignal(str)  # item_id
    drag_started = pyqtSignal(str)  # item_id

    # Visual states
    NORMAL = "normal"
    FOLDER = "folder"
    SELECTED = "selected"
    DROP_TARGET = "drop_target"
    GHOST = "ghost"  # placeholder gap during drag
    DRAGGING = "dragging"  # src slot while being dragged

    def __init__(
        self,
        item: dict,
        cell_size: int,
        font_size: int,
        icon_resolver=None,
        parent=None,
    ):
        super().__init__(parent)
        self._item = item
        self._cell = cell_size
        self._font_size = font_size
        self._icon_resolver = icon_resolver
        self._state = self.FOLDER if item.get("type") == "folder" else self.NORMAL
        self._hovered = False
        self._pixmap: QPixmap | None = None
        self._drag_start: QPointF | None = None

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsWidget.GraphicsItemFlag.ItemIsSelectable, True)
        self.resize(QSizeF(cell_size, cell_size))
        self._load_pixmap()

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def item_id(self) -> str:
        return self._item["id"]

    @property
    def item(self) -> dict:
        return self._item

    def set_item(self, item: dict) -> None:
        """Swap displayed item (used during drag preview)."""
        self._item = item
        self._state = self.FOLDER if item.get("type") == "folder" else self.NORMAL
        self._load_pixmap()
        self.update()

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def set_cell_size(self, size: int, font_size: int) -> None:
        self._cell = size
        self._font_size = font_size
        self.resize(QSizeF(size, size))
        self._load_pixmap()
        self.update()

    def icon_pixmap(self) -> QPixmap | None:
        return self._pixmap

    # ── painting ──────────────────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._cell, self._cell)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        r = self.boundingRect().adjusted(1, 1, -1, -1)
        radius = 10
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._state == self.GHOST:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(C_GHOST_BG)
            painter.drawRoundedRect(r, radius, radius)
            if self._pixmap and not self._pixmap.isNull():
                icon_size = int(self._cell * 0.55)
                px = self._pixmap.scaled(
                    icon_size,
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (self._cell - px.width()) // 2
                y = int(self._cell * 0.12)
                painter.setOpacity(0.25)
                painter.drawPixmap(x, y, px)
                painter.setOpacity(1.0)
            return

        if self._state == self.DRAGGING:
            return  # invisible while being dragged

        if self._state == self.DROP_TARGET:
            painter.setPen(QPen(C_DROP_TARGET_BORDER, 2))
            painter.setBrush(C_DROP_TARGET_BG)
            painter.drawRoundedRect(r, radius, radius)
        elif self._state == self.SELECTED:
            bg = C_SELECTED_HOVER if self._hovered else C_SELECTED_BG
            painter.setPen(QPen(C_SELECTED_BORDER, 2))
            painter.setBrush(bg)
            painter.drawRoundedRect(r, radius, radius)
        elif self._state == self.FOLDER:
            bg = C_FOLDER_HOVER if self._hovered else C_FOLDER_BG
            painter.setPen(QPen(C_FOLDER_BORDER, 1))
            painter.setBrush(bg)
            painter.drawRoundedRect(r, radius, radius)
        elif self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(C_NORMAL_HOVER)
            painter.drawRoundedRect(r, radius, radius)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_TRANSPARENT)
            painter.drawRoundedRect(r, radius, radius)

        # Icon
        if self._pixmap and not self._pixmap.isNull():
            icon_size = int(self._cell * 0.55)
            px = self._pixmap.scaled(
                icon_size,
                icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self._cell - px.width()) // 2
            y = int(self._cell * 0.12)
            painter.drawPixmap(x, y, px)

        # Label
        name = self._item.get("name", "")
        font = QFont()
        font.setPointSize(self._font_size)
        if self._state == self.FOLDER:
            font.setBold(True)
        painter.setFont(font)
        label_y = int(self._cell * 0.72)
        label_rect = QRectF(4, label_y, self._cell - 8, self._cell - label_y - 4)
        fm = painter.fontMetrics()
        name = fm.elidedText(name, Qt.TextElideMode.ElideRight, int(label_rect.width()))
        painter.setPen(_LABEL_COLOR)
        painter.drawText(
            label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, name
        )

    # ── hover ─────────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
        event.accept()
        # do NOT call super() — it would trigger QGraphicsScene selection logic

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_start is not None:
                delta = (event.pos() - self._drag_start).manhattanLength()
                if delta <= 10:
                    self.clicked.emit(self.item_id)
            self._drag_start = None
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        delta = (event.pos() - self._drag_start).manhattanLength()
        if delta > 10:
            self.drag_started.emit(self.item_id)
            self._drag_start = None
        event.accept()

    # ── private ───────────────────────────────────────────────────────────────

    def _load_pixmap(self) -> None:
        icon_size = int(self._cell * 0.55)
        if self._item.get("type") == "folder":
            self._pixmap = folder_pixmap(icon_size)
        else:
            self._pixmap = app_pixmap(self._item, icon_size, self._icon_resolver)
