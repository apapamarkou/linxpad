"""PageScene — one QGraphicsScene representing one page of icons.

Responsibilities:
- Own and position IconItems in a cols×rows grid
- Compute cell geometry from scene size
- Provide hit-testing (item at scene point)
- No drag logic, no page navigation
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsScene

from .icon_item import IconItem


class PageScene(QGraphicsScene):
    """One page of the launcher grid."""

    def __init__(
        self,
        items: list[dict],
        cols: int,
        rows: int,
        cell_size: int,
        font_size: int,
        spacing: int,
        icon_resolver,
        on_item_clicked,
        on_drag_started,
        parent=None,
    ):
        super().__init__(parent)
        self._cols = cols
        self._rows = rows
        self._cell = cell_size
        self._font_size = font_size
        self._spacing = spacing
        self._icon_resolver = icon_resolver
        self._on_item_clicked = on_item_clicked
        self._on_drag_started = on_drag_started

        self._items: list[IconItem] = []
        self._populate(items)

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def icon_items(self) -> list[IconItem]:
        return list(self._items)

    def item_at_pos(self, scene_pos: QPointF) -> IconItem | None:
        """Return the visible IconItem whose cell contains scene_pos."""
        for icon in self._items:
            if icon._state != IconItem.GHOST and icon.sceneBoundingRect().contains(scene_pos):
                return icon
        return None

    def item_by_id(self, item_id: str) -> IconItem | None:
        for icon in self._items:
            if icon.item_id == item_id:
                return icon
        return None

    def set_cell_size(self, cell_size: int, font_size: int) -> None:
        self._cell = cell_size
        self._font_size = font_size
        stride = cell_size + self._spacing
        for i, icon in enumerate(self._items):
            icon.set_cell_size(cell_size, font_size)
            icon.setPos(self._cell_pos(i))
        self.setSceneRect(
            QRectF(0, 0, self._cols * stride - self._spacing, self._rows * stride - self._spacing)
        )

    def grid_pos(self, index: int) -> QPointF:
        return self._cell_pos(index)

    def index_at_pos(self, scene_pos: QPointF) -> int:
        stride = self._cell + self._spacing
        col = max(0, min(self._cols - 1, int(scene_pos.x() / stride)))
        row = max(0, min(self._rows - 1, int(scene_pos.y() / stride)))
        return row * self._cols + col

    def count(self) -> int:
        return len(self._items)

    # ── private ───────────────────────────────────────────────────────────────

    def _populate(self, items: list[dict]) -> None:
        for i, item in enumerate(items):
            icon = self._make_icon(item)
            icon.setPos(self._cell_pos(i))
            self.addItem(icon)
            self._items.append(icon)
        stride = self._cell + self._spacing
        self.setSceneRect(
            QRectF(0, 0, self._cols * stride - self._spacing, self._rows * stride - self._spacing)
        )

    def _make_icon(self, item: dict) -> IconItem:
        icon = IconItem(
            item=item,
            cell_size=self._cell,
            font_size=self._font_size,
            icon_resolver=self._icon_resolver,
        )
        icon.clicked.connect(
            lambda item_id, i=item: self._on_item_clicked(item_id, i.get("type", "app"))
        )
        icon.drag_started.connect(self._on_drag_started)
        return icon

    def _cell_pos(self, index: int) -> QPointF:
        row, col = divmod(index, self._cols)
        return QPointF(col * (self._cell + self._spacing), row * (self._cell + self._spacing))
