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

"""GridView — QGraphicsView managing multiple pages of PageScenes.

Responsibilities:
- Create/destroy PageScenes per page
- Animate page transitions (horizontal slide)
- Coordinate DragHandler across pages
- Expose public API matching the old PagedGridView contract
- Emit signals for all user actions (no business logic here)
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QMimeData,
    QPoint,
    QPointF,
    QPropertyAnimation,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QDrag, QNativeGestureEvent, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget

from .drag_handler import DragHandler
from .page_scene import PageScene


class GridView(QGraphicsView):
    """Paged QGraphicsView launcher grid with animated transitions and drag-drop."""

    # ── signals ───────────────────────────────────────────────────────────────
    item_clicked = pyqtSignal(str, str)  # item_id, item_type
    reorder_requested = pyqtSignal(str, str, str)  # dragged_id, target_id, placement
    button_drop_requested = pyqtSignal(str, str, str)  # src_id, dst_id, dst_type
    move_to_page_requested = pyqtSignal(str, int)  # item_id, page
    move_to_slot_requested = pyqtSignal(str, int)  # item_id, target_page
    page_changed = pyqtSignal(int)
    drag_started = pyqtSignal()
    drag_ended = pyqtSignal()
    background_clicked = pyqtSignal()  # click on empty grid area
    anim_started = pyqtSignal()
    anim_ended = pyqtSignal()
    close_requested = pyqtSignal()  # pinch-to-close gesture

    def __init__(
        self,
        cols: int,
        rows: int,
        font_size: int,
        spacing: int,
        icon_resolver,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._cols = cols
        self._rows = rows
        self._font_size = font_size
        self._spacing = spacing
        self._icon_resolver = icon_resolver
        self._cell = 80  # computed on first resize
        self._current_page = 0
        self._pages: list[PageScene] = []
        self._animating = False

        self._drag = DragHandler(
            on_reorder=lambda *a: self.reorder_requested.emit(*a),
            on_button_drop=lambda *a: self.button_drop_requested.emit(*a),
            on_move_to_page=lambda *a: self.move_to_page_requested.emit(*a),
            cols=cols,
        )

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setRenderHint(self.renderHints() | self.renderHints().Antialiasing)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        # Accumulated horizontal pixel delta for touchpad swipe gesture.
        # A swipe must exceed this threshold (px) before flipping the page,
        # preventing accidental flips from tiny touchpad movements.
        self._swipe_accum: float = 0.0
        self._SWIPE_THRESHOLD = 120

        # Accumulated pinch zoom delta. Pinching in (negative total) closes.
        self._pinch_accum: float = 0.0
        self._PINCH_THRESHOLD = 0.3

        # Empty placeholder scene so the view is never sceneless
        self.setScene(QGraphicsScene(self))

    # ── private helpers ───────────────────────────────────────────────────────

    def _make_scene(self, items: list[dict]) -> PageScene:
        return PageScene(
            items=items,
            cols=self._cols,
            rows=self._rows,
            cell_size=self._cell,
            font_size=self._font_size,
            spacing=self._spacing,
            icon_resolver=self._icon_resolver,
            on_item_clicked=lambda item_id, item_type: self.item_clicked.emit(item_id, item_type),
            on_drag_started=lambda item_id: self._start_drag_for(item_id),
        )

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def page_count(self) -> int:
        return len(self._pages)

    def load_pages(self, pages: list[list[dict]]) -> None:
        """Replace all pages with new data."""
        self._pages.clear()
        self._animating = False
        for page_items in pages:
            self._pages.append(self._make_scene(page_items))
        if not self._pages:
            self._pages.append(self._make_scene([]))
        self._current_page = min(self._current_page, len(self._pages) - 1)
        self._show_page_silent(self._current_page)

    def go_to_page(self, index: int) -> None:
        if 0 <= index < len(self._pages) and index != self._current_page and not self._animating:
            self._swipe_accum = 0.0
            self._animate_to_page(index)

    def next_page(self) -> None:
        self.go_to_page(self._current_page + 1)

    def prev_page(self) -> None:
        self.go_to_page(self._current_page - 1)

    def append_empty_page(self) -> None:
        self._pages.append(self._make_scene([]))

    def remove_trailing_empty_page(self) -> None:
        if len(self._pages) <= 1:
            return
        if self._pages[-1].count() == 0:
            self._pages.pop()
            if self._current_page >= len(self._pages):
                self._current_page = len(self._pages) - 1
                self._show_page_silent(self._current_page)

    def current_scene(self) -> PageScene | None:
        if 0 <= self._current_page < len(self._pages):
            return self._pages[self._current_page]
        return None

    def scene_at(self, page: int) -> PageScene | None:
        if 0 <= page < len(self._pages):
            return self._pages[page]
        return None

    # ── resize ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._recompute_cell()

    def _recompute_cell(self) -> None:
        w, h = self.viewport().width(), self.viewport().height()
        if w <= 0 or h <= 0:
            return
        usable_w = w - self._spacing * (self._cols - 1)
        usable_h = h - self._spacing * (self._rows - 1)
        cell = max(40, min(usable_w // self._cols, usable_h // self._rows))
        if cell == self._cell:
            return
        self._cell = cell
        for scene in self._pages:
            scene.set_cell_size(cell, self._font_size)
        scene = self.current_scene()
        if scene:
            self.setSceneRect(scene.sceneRect())

    # ── page animation ────────────────────────────────────────────────────────

    def _show_page_silent(self, index: int) -> None:
        self._current_page = index
        scene = self._pages[index]
        scene.set_cell_size(self._cell, self._font_size)
        self.setScene(scene)
        self.setSceneRect(scene.sceneRect())
        self.page_changed.emit(index)

    def _animate_to_page(self, index: int) -> None:
        direction = 1 if index > self._current_page else -1
        old_scene = self.current_scene()
        new_scene = self._pages[index]
        new_scene.set_cell_size(self._cell, self._font_size)
        w = self.width()
        geo = self.geometry()

        # Incoming page — created first so it sits below outgoing
        in_view = QGraphicsView(new_scene, self.parent())
        in_view.setStyleSheet("background: transparent; border: none;")
        in_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        in_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        in_view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        in_view.setSceneRect(new_scene.sceneRect())
        in_view.setGeometry(geo.translated(direction * w, 0))
        in_view.show()

        # Outgoing page — raised on top so it's visible sliding out
        out_view = QGraphicsView(old_scene, self.parent())
        out_view.setStyleSheet("background: transparent; border: none;")
        out_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        out_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        out_view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        out_view.setSceneRect(old_scene.sceneRect())
        out_view.setGeometry(geo)
        out_view.show()
        out_view.raise_()

        self._animating = True
        self._current_page = index
        self.anim_started.emit()

        anim_out = QPropertyAnimation(out_view, b"pos", self)
        anim_out.setDuration(500)
        anim_out.setStartValue(QPoint(0, 0))
        anim_out.setEndValue(QPoint(-direction * w, 0))
        anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim_in = QPropertyAnimation(in_view, b"pos", self)
        anim_in.setDuration(500)
        anim_in.setStartValue(QPoint(direction * w, 0))
        anim_in.setEndValue(QPoint(0, 0))
        anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _done():
            out_view.hide()
            out_view.deleteLater()
            in_view.hide()
            in_view.deleteLater()
            self.setScene(new_scene)
            self.setSceneRect(new_scene.sceneRect())
            self._animating = False
            self.anim_ended.emit()
            self.page_changed.emit(index)

        anim_in.finished.connect(_done)
        anim_out.start()
        anim_in.start()

    # ── wheel / touchpad swipe ────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        px = event.pixelDelta()
        if px.x() != 0:
            # Smooth touchpad scroll: accumulate horizontal pixels.
            self._swipe_accum += px.x()
            if self._swipe_accum <= -self._SWIPE_THRESHOLD:
                self._swipe_accum = 0.0
                self.next_page()
            elif self._swipe_accum >= self._SWIPE_THRESHOLD:
                self._swipe_accum = 0.0
                self.prev_page()
        elif px.y() != 0:
            # Vertical smooth scroll — ignore (don't flip pages).
            pass
        else:
            # Classic click-wheel (angleDelta only): flip immediately.
            delta = event.angleDelta()
            if delta.x() != 0:
                if delta.x() < 0:
                    self.next_page()
                else:
                    self.prev_page()
            elif delta.y() != 0:
                if delta.y() < 0:
                    self.next_page()
                else:
                    self.prev_page()
        event.accept()

    def event(self, event) -> bool:
        if isinstance(event, QNativeGestureEvent):
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self._pinch_accum += event.value()
                if self._pinch_accum <= -self._PINCH_THRESHOLD:
                    self._pinch_accum = 0.0
                    self.close_requested.emit()
                elif self._pinch_accum > 0:
                    # Pinching out resets — no action
                    self._pinch_accum = 0.0
                event.accept()
                return True
        return super().event(event)

    # ── drag/drop ─────────────────────────────────────────────────────────────

    def _scene_pos(self, view_pos: QPoint) -> QPointF:
        return self.mapToScene(view_pos)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            scene = self.current_scene()
            hit = scene.item_at_pos(scene_pos) if scene else None
            if hit is None:
                self.background_clicked.emit()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)

    def _start_drag_for(self, item_id: str) -> None:
        scene = self.current_scene()
        if scene is None:
            return
        icon = scene.item_by_id(item_id)
        if icon is None:
            return
        self._drag.start(icon, self._current_page, scene)
        self.drag_started.emit()

        # Start Qt drag
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
        # After drag.exec returns
        if self._drag.active:
            scene = self.current_scene()
            if scene:
                self._drag.cancel(scene)
        self.drag_ended.emit()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText() and event.mimeData().text().startswith("item:"):
            item_id = event.mimeData().text().replace("item:", "")
            if not self._drag.active:
                scene = self.current_scene()
                if scene:
                    icon = scene.item_by_id(item_id)
                    if icon:
                        self._drag.start(icon, self._current_page, scene)
                        self.drag_started.emit()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._drag.active:
            event.ignore()
            return
        scene = self.current_scene()
        if scene:
            self._drag.update_preview(scene, self._scene_pos(event.position().toPoint()))
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        # Do not cancel the drag session here — the cursor may have moved to a
        # flip zone widget (sibling of this view). The session is cleaned up
        # after drag.exec() returns in _start_drag_for.
        pass

    def dropEvent(self, event) -> None:
        if not self._drag.active:
            event.ignore()
            return
        scene = self.current_scene()
        if scene:
            self._drag.finish_drop(
                scene,
                self._scene_pos(event.position().toPoint()),
                self._current_page,
            )
        self.drag_ended.emit()
        event.acceptProposedAction()
