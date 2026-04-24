"""Tests for DragHandler — session lifecycle and insert index computation."""

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from linxpad.ui.graphics.drag_handler import DragHandler, DragSession
from linxpad.ui.graphics.icon_item import IconItem
from linxpad.ui.graphics.page_scene import PageScene

_ITEMS = [
    {"id": f"app{i}", "name": f"App {i}", "type": "app", "exec": f"app{i}.desktop"}
    for i in range(4)
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_scene(items=None, cols=4, rows=1, cell=80, spacing=10):
    return PageScene(
        items=items if items is not None else _ITEMS,
        cols=cols,
        rows=rows,
        cell_size=cell,
        font_size=11,
        spacing=spacing,
        icon_resolver=None,
        on_item_clicked=lambda *_: None,
        on_drag_started=lambda *_: None,
    )


def _make_handler():
    reorders, drops, moves = [], [], []
    handler = DragHandler(
        on_reorder=lambda *a: reorders.append(a),
        on_button_drop=lambda *a: drops.append(a),
        on_move_to_page=lambda *a: moves.append(a),
        cols=4,
    )
    return handler, reorders, drops, moves


class TestDragSessionDataclass:
    def test_default_compact_items_empty(self):
        s = DragSession(src_id="x", src_page=0, src_index=0)
        assert s.compact_items == []

    def test_default_last_insert_idx_none(self):
        s = DragSession(src_id="x", src_page=0, src_index=0)
        assert s.last_insert_idx is None

    def test_default_foreign_ghost_none(self):
        s = DragSession(src_id="x", src_page=0, src_index=0)
        assert s.foreign_ghost is None


class TestDragHandlerLifecycle:
    def test_not_active_before_start(self, qapp):
        handler, *_ = _make_handler()
        assert not handler.active

    def test_active_after_start(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[0]
        handler.start(icon, 0, scene)
        assert handler.active

    def test_src_id_after_start(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[1]
        handler.start(icon, 0, scene)
        assert handler.src_id == "app1"

    def test_src_icon_state_is_dragging(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[0]
        handler.start(icon, 0, scene)
        assert icon._state == IconItem.DRAGGING

    def test_compact_items_excludes_src(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[0]
        handler.start(icon, 0, scene)
        ids = [it["id"] for it in handler._session.compact_items]
        assert "app0" not in ids
        assert len(ids) == 3

    def test_not_active_after_cancel(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        handler.start(scene.icon_items[0], 0, scene)
        handler.cancel(scene)
        assert not handler.active

    def test_src_id_none_after_cancel(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        handler.start(scene.icon_items[0], 0, scene)
        handler.cancel(scene)
        assert handler.src_id is None

    def test_icons_restored_after_cancel(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        handler.start(scene.icon_items[0], 0, scene)
        handler.cancel(scene)
        for icon in scene.icon_items:
            assert icon._state in (IconItem.NORMAL, IconItem.FOLDER)


class TestDragHandlerInsertIndex:
    """Test _compute_insert_idx with a 4-column, 1-row scene."""

    def test_left_half_of_first_slot_inserts_before(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1, cell=80, spacing=10)
        compact = [it.item for it in scene.icon_items]
        # x=20 is left half of slot 0 (centre at 40)
        idx = handler._compute_insert_idx(scene, QPointF(20, 40), compact)
        assert idx == 0

    def test_right_half_of_first_slot_inserts_after(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1, cell=80, spacing=10)
        compact = [it.item for it in scene.icon_items]
        # x=60 is right half of slot 0
        idx = handler._compute_insert_idx(scene, QPointF(60, 40), compact)
        assert idx == 1

    def test_left_half_of_second_slot_inserts_before_second(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1, cell=80, spacing=10)
        compact = [it.item for it in scene.icon_items]
        stride = 80 + 10
        # x = stride + 20 → left half of slot 1
        idx = handler._compute_insert_idx(scene, QPointF(stride + 20, 40), compact)
        assert idx == 1

    def test_right_half_of_last_slot_inserts_at_end(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1, cell=80, spacing=10)
        compact = [it.item for it in scene.icon_items]
        stride = 80 + 10
        # x = 3*stride + 60 → right half of slot 3
        idx = handler._compute_insert_idx(scene, QPointF(3 * stride + 60, 40), compact)
        assert idx == 4

    def test_empty_compact_returns_zero(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1)
        idx = handler._compute_insert_idx(scene, QPointF(40, 40), [])
        assert idx == 0

    def test_result_always_in_valid_range(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene(cols=4, rows=1, cell=80, spacing=10)
        compact = [it.item for it in scene.icon_items]
        for x in range(0, 400, 20):
            idx = handler._compute_insert_idx(scene, QPointF(x, 40), compact)
            assert 0 <= idx <= len(compact)


class TestDragHandlerFinishDrop:
    def test_reorder_emitted_on_gap_drop(self, qapp):
        handler, reorders, drops, moves = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[0]
        handler.start(icon, 0, scene)
        # Drop at right half of slot 1 → insert after app1
        stride = 80 + 10
        handler.finish_drop(scene, QPointF(stride + 60, 40), 0)
        assert len(reorders) == 1
        assert reorders[0][0] == "app0"  # dragged_id

    def test_button_drop_emitted_on_icon_hit(self, qapp):
        handler, reorders, drops, moves = _make_handler()
        scene = _make_scene()
        icon = scene.icon_items[0]
        handler.start(icon, 0, scene)
        # Drop on centre third of app2 (slot 2)
        stride = 80 + 10
        centre_x = 2 * stride + 40  # exact centre of slot 2
        handler.finish_drop(scene, QPointF(centre_x, 40), 0)
        assert len(drops) == 1
        assert drops[0][0] == "app0"
        assert drops[0][1] == "app2"

    def test_not_active_after_finish(self, qapp):
        handler, *_ = _make_handler()
        scene = _make_scene()
        handler.start(scene.icon_items[0], 0, scene)
        handler.finish_drop(scene, QPointF(40, 40), 0)
        assert not handler.active
