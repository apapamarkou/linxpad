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
 
"""FolderView — QGraphicsView grid for folder contents.

Mirrors GridView: DragHandler for in-folder reorder, Qt drag that escapes
to the window for remove-from-folder, background click to return to main.
"""

from __future__ import annotations

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap
from PyQt6.QtWidgets import QGraphicsView, QWidget

from ..graphics.drag_handler import DragHandler
from ..graphics.page_scene import PageScene


class FolderView(QGraphicsView):
    """Single-page graphics view for folder contents."""

    item_clicked = pyqtSignal(str, str)  # item_id, item_type
    reorder_requested = pyqtSignal(str, str, str)  # dragged_id, target_id, placement
    background_clicked = pyqtSignal()

    def __init__(
        self, cols: int, font_size: int, spacing: int, icon_resolver, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._cols = cols
        self._font_size = font_size
        self._spacing = spacing
        self._icon_resolver = icon_resolver
        self._cell = 80
        self._scene: PageScene | None = None

        self._drag = DragHandler(
            on_reorder=lambda *a: self.reorder_requested.emit(*a),
            on_button_drop=lambda *a: None,
            on_move_to_page=lambda *a: None,
            cols=cols,
        )

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setRenderHint(self.renderHints() | self.renderHints().Antialiasing)
        self.setStyleSheet("background: #3d3d3d; border: 1px solid #555; border-radius: 12px;")
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

    # ── public API ────────────────────────────────────────────────────────────

    def load_items(self, items: list[dict], cell: int) -> None:
        rows = max(1, (len(items) + self._cols - 1) // self._cols)
        self._cell = cell
        self._scene = PageScene(
            items=items,
            cols=self._cols,
            rows=rows,
            cell_size=cell,
            font_size=self._font_size,
            spacing=self._spacing,
            icon_resolver=self._icon_resolver,
            on_item_clicked=lambda iid, itype: self.item_clicked.emit(iid, itype),
            on_drag_started=self._start_drag_for,
        )
        self.setScene(self._scene)
        self.setSceneRect(self._scene.sceneRect())

    # ── resize ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._scene is None:
            return
        vp = self.viewport()
        w = vp.width() if vp else self.width()
        usable = w - self._spacing * (self._cols - 1)
        cell = max(40, usable // self._cols)
        if cell != self._cell:
            self._cell = cell
            self._scene.set_cell_size(cell, self._font_size)
            self.setSceneRect(self._scene.sceneRect())

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._scene:
            scene_pos = self.mapToScene(event.position().toPoint())
            if self._scene.item_at_pos(scene_pos) is None:
                self.background_clicked.emit()
                return
        super().mousePressEvent(event)

    # ── drag/drop ─────────────────────────────────────────────────────────────

    def _start_drag_for(self, item_id: str) -> None:
        if self._scene is None:
            return
        icon = self._scene.item_by_id(item_id)
        if icon is None:
            return
        self._drag.start(icon, 0, self._scene)

        drag = QDrag(self.viewport())
        mime = QMimeData()
        mime.setText(f"item:{item_id}")
        drag.setMimeData(mime)
        if icon.icon_pixmap():
            px = icon.icon_pixmap()
            ghost = QPixmap(px.size())
            ghost.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter

            p = QPainter(ghost)
            p.setOpacity(0.5)
            p.drawPixmap(0, 0, px)
            p.end()
            drag.setPixmap(ghost)
            drag.setHotSpot(ghost.rect().center())

        drag.exec(Qt.DropAction.MoveAction)

        # Cleanup after drag ends (drop happened elsewhere or was cancelled)
        if self._drag.active and self._scene:
            self._drag.cancel(self._scene)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText() and event.mimeData().text().startswith("item:"):
            item_id = event.mimeData().text().replace("item:", "")
            if not self._drag.active and self._scene:
                icon = self._scene.item_by_id(item_id)
                if icon:
                    self._drag.start(icon, 0, self._scene)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._drag.active:
            event.ignore()
            return
        if self._scene:
            self._drag.update_preview(self._scene, self.mapToScene(event.position().toPoint()))
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        # Cursor left the view — the window's dropEvent will handle removal.
        # Cancel the reorder preview but keep the Qt drag alive.
        if self._drag.active and self._scene:
            self._drag.cancel(self._scene)

    def dropEvent(self, event) -> None:
        if not self._drag.active:
            event.ignore()
            return
        if self._scene:
            self._drag.finish_drop(
                self._scene,
                self.mapToScene(event.position().toPoint()),
                0,
            )
        event.acceptProposedAction()
