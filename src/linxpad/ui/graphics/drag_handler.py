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

"""DragHandler — all drag-and-drop logic for the grid view.

Responsibilities:
- Track drag session state
- Compute insert positions from cursor geometry
- Animate icon positions during drag (slide to new slots)
- Emit drop actions: reorder, button_drop, move_to_page
- No knowledge of pages navigation or window layout
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation
from PyQt6.QtGui import QPixmap

from .icon_item import IconItem
from .page_scene import PageScene


@dataclass
class DragSession:
    src_id: str
    src_page: int
    src_index: int
    src_scene: object = None  # PageScene — stored for cancel-on-source
    src_pixmap: QPixmap | None = None
    compact_items: list[dict] = field(default_factory=list)
    last_insert_idx: int | None = None
    foreign_ghost: IconItem | None = None


class DragHandler:
    """Manages the full drag lifecycle for a GridView."""

    ANIM_MS = 150

    def __init__(
        self,
        on_reorder: Callable,
        on_button_drop: Callable,
        on_move_to_page: Callable,
        cols: int,
    ):
        self._on_reorder = on_reorder
        self._on_button_drop = on_button_drop
        self._on_move_to_page = on_move_to_page
        self._cols = cols
        self._session: DragSession | None = None
        self._anims: list[QPropertyAnimation] = []

    # ── public ────────────────────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        return self._session is not None

    @property
    def src_id(self) -> str | None:
        return self._session.src_id if self._session else None

    def start(self, icon: IconItem, page_idx: int, scene: PageScene) -> None:
        idx = scene.icon_items.index(icon)
        self._session = DragSession(
            src_id=icon.item_id,
            src_page=page_idx,
            src_index=idx,
            src_scene=scene,
            src_pixmap=icon.icon_pixmap(),
            compact_items=[it.item for it in scene.icon_items if it.item_id != icon.item_id],
        )
        icon.set_state(IconItem.DRAGGING)
        # Close the gap left by the removed icon
        others = [it for it in scene.icon_items if it.item_id != icon.item_id]
        for i, other in enumerate(others):
            self._animate_to(other, scene.grid_pos(i))

    def update_preview(self, scene: PageScene, scene_pos: QPointF) -> None:
        """Update ghost gap and drop-target highlights for current cursor pos."""
        if self._session is None:
            return
        d = self._session

        # Check if cursor is over a real icon (drop-target intent)
        hit = self._hit_icon(scene, scene_pos)
        if hit is not None and hit.item_id != d.src_id:
            self._clear_gap(scene)
            self._clear_drop_targets(scene, exclude=hit)
            hit.set_state(IconItem.DROP_TARGET)
            d.last_insert_idx = None
            return

        self._clear_drop_targets(scene)

        # Cross-page drag onto a full destination page — no gap preview
        cross_page = next((it for it in scene.icon_items if it.item_id == d.src_id), None) is None
        if cross_page and scene.count() >= scene._cols * scene._rows:
            self._clear_gap(scene)
            d.last_insert_idx = None
            return

        # Compute insert index
        cross_page = next((it for it in scene.icon_items if it.item_id == d.src_id), None) is None
        compact = (
            [it.item for it in scene.icon_items if it.item_id != "__ghost__"]
            if cross_page
            else d.compact_items
        )
        insert_idx = self._compute_insert_idx(scene, scene_pos, compact)
        if insert_idx == d.last_insert_idx:
            return
        d.last_insert_idx = insert_idx
        self._apply_gap_preview(scene, insert_idx, d)

    def finish_drop(self, scene: PageScene, scene_pos: QPointF, current_page: int) -> None:
        """Resolve the drop and emit the appropriate callback."""
        if self._session is None:
            return
        d = self._session
        src_id = d.src_id

        # Drop on a real icon → folder create / add to folder
        hit = self._hit_icon(scene, scene_pos)
        if hit is not None and hit.item_id != src_id:
            self._end_session(scene)
            self._on_button_drop(src_id, hit.item_id, hit.item.get("type"))
            return

        # Empty page — only the flip zone handles drops onto blank pages
        real = [it for it in scene.icon_items if it._state != IconItem.GHOST]
        if not real:
            self._end_session(scene)
            return

        # Reorder / insert
        cross_page = next((it for it in scene.icon_items if it.item_id == d.src_id), None) is None
        if cross_page:
            compact = [it.item for it in scene.icon_items if it.item_id != "__ghost__"]
            # Full destination page — cancel and restore icon to source
            if scene.count() >= scene._cols * scene._rows:
                self._end_session(d.src_scene)
                return
        else:
            compact = d.compact_items
        if not compact:
            self._end_session(scene)
            self._on_move_to_page(src_id, current_page)
            return

        insert_idx = d.last_insert_idx
        if insert_idx is None:
            insert_idx = self._compute_insert_idx(scene, scene_pos, compact)
        insert_idx = max(0, min(insert_idx, len(compact)))

        if insert_idx == 0:
            target_id, placement = compact[0]["id"], "before"
        elif insert_idx >= len(compact):
            target_id, placement = compact[-1]["id"], "after"
        else:
            target_id, placement = compact[insert_idx]["id"], "before"

        self._end_session(scene)
        self._on_reorder(src_id, target_id, placement)

    def cancel(self, scene: PageScene) -> None:
        self._end_session(scene)

    # ── private ───────────────────────────────────────────────────────────────

    def _hit_icon(self, scene: PageScene, pos: QPointF) -> IconItem | None:
        """Return icon only when cursor is in its center third (folder-drop intent)."""
        for icon in scene.icon_items:
            if icon._state in (IconItem.GHOST, IconItem.DRAGGING):
                continue
            r = icon.sceneBoundingRect()
            if not r.contains(pos):
                continue
            # Only the middle third horizontally triggers a folder drop
            third = r.width() / 3
            if r.left() + third <= pos.x() <= r.right() - third:
                return icon
        return None

    def _compute_insert_idx(self, scene: PageScene, pos: QPointF, compact: list[dict]) -> int:
        """Map cursor position to an insert index using grid slot geometry."""
        if not compact:
            return 0
        # Use logical grid positions (slot 0..N-1 in compact order)
        # Each compact item maps to a grid slot; find which slot the cursor is over.
        stride = scene._cell + scene._spacing
        cols = scene._cols
        col = int(pos.x() / stride)
        row = int(pos.y() / stride)
        col = max(0, min(cols - 1, col))
        row = max(0, min((len(compact) - 1) // cols, row))
        slot = row * cols + col
        slot = max(0, min(len(compact) - 1, slot))
        # Left half → insert before, right half → insert after
        slot_x = slot % cols * stride
        placement = "after" if pos.x() >= slot_x + scene._cell / 2 else "before"
        return min(slot + (1 if placement == "after" else 0), len(compact))

    def _apply_gap_preview(self, scene: PageScene, insert_idx: int, d: DragSession) -> None:
        """Animate icons to their new positions with a gap at insert_idx."""
        drag_icon = next((it for it in scene.icon_items if it.item_id == d.src_id), None)
        cross_page = drag_icon is None

        if cross_page:
            # Destination page: all its icons shift to make room for the ghost.
            # Use a temporary ghost item stored in the session.
            others = list(scene.icon_items)
            compact = [it.item for it in others]
            preview: list[dict | None] = compact[:insert_idx] + [None] + compact[insert_idx:]
            self._stop_anims()
            if d.foreign_ghost is None:
                d.foreign_ghost = IconItem(
                    item={"id": "__ghost__", "name": ""},
                    cell_size=scene._cell,
                    font_size=scene._font_size,
                    icon_resolver=None,
                )
                d.foreign_ghost._pixmap = d.src_pixmap
                d.foreign_ghost.set_state(IconItem.GHOST)
                scene.addItem(d.foreign_ghost)
            ghost = d.foreign_ghost
            by_id = {it.item_id: it for it in others}
            others_iter = iter([by_id[item["id"]] for item in compact])
            for slot, item_or_none in enumerate(preview):
                target_pos = scene.grid_pos(slot)
                if item_or_none is None:
                    self._animate_to(ghost, target_pos)
                else:
                    self._animate_to(next(others_iter), target_pos)
        else:
            # Same page: reuse the dragging icon as the ghost widget.
            compact = d.compact_items
            preview = compact[:insert_idx] + [None] + compact[insert_idx:]
            by_id = {it.item_id: it for it in scene.icon_items if it.item_id != d.src_id}
            others_iter = iter([by_id[item["id"]] for item in compact])
            self._stop_anims()
            for slot, item_or_none in enumerate(preview):
                target_pos = scene.grid_pos(slot)
                if item_or_none is None:
                    drag_icon.set_state(IconItem.GHOST)
                    self._animate_to(drag_icon, target_pos)
                else:
                    icon = next(others_iter)
                    if icon._state == IconItem.GHOST:
                        icon.set_state(
                            IconItem.FOLDER
                            if icon.item.get("type") == "folder"
                            else IconItem.NORMAL
                        )
                    self._animate_to(icon, target_pos)

    def _animate_to(self, icon: IconItem, target: QPointF) -> None:
        if icon.pos() == target:
            return
        anim = QPropertyAnimation(icon, b"pos")
        anim.setDuration(self.ANIM_MS)
        anim.setStartValue(icon.pos())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anims.append(anim)

    def _stop_anims(self) -> None:
        for a in self._anims:
            a.stop()
        self._anims.clear()

    def _clear_gap(self, scene: PageScene) -> None:
        d = self._session
        self._stop_anims()
        # Remove foreign ghost if present
        if d.foreign_ghost is not None:
            scene.removeItem(d.foreign_ghost)
            d.foreign_ghost = None
        drag_icon = next((it for it in scene.icon_items if it.item_id == d.src_id), None)
        if drag_icon is not None:
            drag_icon.set_state(IconItem.DRAGGING)
        by_id = {it.item_id: it for it in scene.icon_items if it.item_id != d.src_id}
        others = [by_id[item["id"]] for item in d.compact_items if item["id"] in by_id]
        for i, icon in enumerate(others):
            if icon._state == IconItem.GHOST:
                icon.set_state(
                    IconItem.FOLDER if icon.item.get("type") == "folder" else IconItem.NORMAL
                )
            self._animate_to(icon, scene.grid_pos(i))

    def _clear_drop_targets(self, scene: PageScene, exclude: IconItem | None = None) -> None:
        for icon in scene.icon_items:
            if icon is not exclude and icon._state == IconItem.DROP_TARGET:
                icon.set_state(
                    IconItem.FOLDER if icon.item.get("type") == "folder" else IconItem.NORMAL
                )

    def _end_session(self, scene: PageScene) -> None:
        self._stop_anims()
        if self._session is None:
            return
        if self._session.foreign_ghost is not None:
            scene.removeItem(self._session.foreign_ghost)
            self._session.foreign_ghost = None
        # Restore all icons to true positions and states
        for i, icon in enumerate(scene.icon_items):
            icon.set_state(
                IconItem.FOLDER if icon.item.get("type") == "folder" else IconItem.NORMAL
            )
            icon.setPos(scene.grid_pos(i))
        self._session = None
