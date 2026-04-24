"""Tests for PageScene — item positioning and hit-testing."""

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from linxpad.ui.graphics.page_scene import PageScene

_ITEMS = [
    {"id": f"app{i}", "name": f"App {i}", "type": "app", "exec": f"app{i}.desktop"}
    for i in range(6)
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_scene(items=None, cols=3, rows=2, cell=80, spacing=10):
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


class TestPageScenePopulation:
    def test_count_matches_items(self, qapp):
        scene = _make_scene()
        assert scene.count() == 6

    def test_empty_scene_has_zero_count(self, qapp):
        scene = _make_scene(items=[])
        assert scene.count() == 0

    def test_icon_items_length(self, qapp):
        scene = _make_scene()
        assert len(scene.icon_items) == 6

    def test_icon_items_returns_copy(self, qapp):
        scene = _make_scene()
        copy = scene.icon_items
        copy.clear()
        assert scene.count() == 6


class TestPageScenePositioning:
    def test_first_item_at_origin(self, qapp):
        scene = _make_scene()
        pos = scene.icon_items[0].pos()
        assert pos == QPointF(0, 0)

    def test_second_item_offset_by_stride(self, qapp):
        cell, spacing = 80, 10
        scene = _make_scene(cell=cell, spacing=spacing)
        stride = cell + spacing
        pos = scene.icon_items[1].pos()
        assert pos == QPointF(stride, 0)

    def test_fourth_item_starts_second_row(self, qapp):
        cell, spacing, cols = 80, 10, 3
        scene = _make_scene(cell=cell, spacing=spacing, cols=cols)
        stride = cell + spacing
        pos = scene.icon_items[3].pos()
        assert pos == QPointF(0, stride)

    def test_grid_pos_matches_item_pos(self, qapp):
        scene = _make_scene()
        for i, icon in enumerate(scene.icon_items):
            assert icon.pos() == scene.grid_pos(i)

    def test_scene_rect_covers_grid(self, qapp):
        cell, spacing, cols, rows = 80, 10, 3, 2
        scene = _make_scene(cell=cell, spacing=spacing, cols=cols, rows=rows)
        r = scene.sceneRect()
        expected_w = cols * (cell + spacing) - spacing
        expected_h = rows * (cell + spacing) - spacing
        assert r.width() == expected_w
        assert r.height() == expected_h


class TestPageSceneHitTesting:
    def test_item_at_pos_returns_correct_item(self, qapp):
        scene = _make_scene()
        # Centre of first cell
        hit = scene.item_at_pos(QPointF(40, 40))
        assert hit is not None
        assert hit.item_id == "app0"

    def test_item_at_pos_second_column(self, qapp):
        cell, spacing = 80, 10
        scene = _make_scene(cell=cell, spacing=spacing)
        stride = cell + spacing
        hit = scene.item_at_pos(QPointF(stride + 40, 40))
        assert hit is not None
        assert hit.item_id == "app1"

    def test_item_at_pos_second_row(self, qapp):
        cell, spacing, cols = 80, 10, 3
        scene = _make_scene(cell=cell, spacing=spacing, cols=cols)
        stride = cell + spacing
        hit = scene.item_at_pos(QPointF(40, stride + 40))
        assert hit is not None
        assert hit.item_id == "app3"

    def test_item_at_pos_returns_none_in_spacing_gap(self, qapp):
        cell, spacing = 80, 10
        scene = _make_scene(cell=cell, spacing=spacing)
        # Point in the spacing gap between col 0 and col 1
        hit = scene.item_at_pos(QPointF(cell + spacing / 2, 40))
        assert hit is None

    def test_item_at_pos_ghost_not_returned(self, qapp):
        from linxpad.ui.graphics.icon_item import IconItem

        scene = _make_scene()
        scene.icon_items[0].set_state(IconItem.GHOST)
        hit = scene.item_at_pos(QPointF(40, 40))
        assert hit is None or hit.item_id != "app0"


class TestPageSceneLookup:
    def test_item_by_id_found(self, qapp):
        scene = _make_scene()
        icon = scene.item_by_id("app2")
        assert icon is not None
        assert icon.item_id == "app2"

    def test_item_by_id_not_found(self, qapp):
        scene = _make_scene()
        assert scene.item_by_id("nonexistent") is None


class TestPageSceneSetCellSize:
    def test_set_cell_size_repositions_items(self, qapp):
        scene = _make_scene(cell=80, spacing=10)
        scene.set_cell_size(100, 12)
        stride = 100 + 10
        assert scene.icon_items[1].pos() == QPointF(stride, 0)

    def test_set_cell_size_updates_scene_rect(self, qapp):
        cols, rows, spacing = 3, 2, 10
        scene = _make_scene(cols=cols, rows=rows, cell=80, spacing=spacing)
        scene.set_cell_size(100, 12)
        r = scene.sceneRect()
        assert r.width() == cols * (100 + spacing) - spacing
        assert r.height() == rows * (100 + spacing) - spacing


class TestPageSceneIndexAtPos:
    def test_index_at_origin(self, qapp):
        scene = _make_scene()
        assert scene.index_at_pos(QPointF(0, 0)) == 0

    def test_index_second_column(self, qapp):
        cell, spacing = 80, 10
        scene = _make_scene(cell=cell, spacing=spacing)
        stride = cell + spacing
        assert scene.index_at_pos(QPointF(stride + 5, 5)) == 1

    def test_index_clamped_to_bounds(self, qapp):
        scene = _make_scene(cols=3, rows=2)
        # Far outside the grid
        idx = scene.index_at_pos(QPointF(9999, 9999))
        assert 0 <= idx < 6
