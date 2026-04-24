"""Tests for IconItem — state transitions and geometry."""

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QPointF, QSizeF
from PyQt6.QtWidgets import QApplication

from linxpad.ui.graphics.icon_item import IconItem

_APP = {"id": "app1", "name": "Firefox", "type": "app", "exec": "firefox.desktop"}
_FOLDER = {"id": "fld1", "name": "My Folder", "type": "folder"}


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def app_icon(qapp):
    return IconItem(item=_APP, cell_size=80, font_size=11)


@pytest.fixture
def folder_icon(qapp):
    return IconItem(item=_FOLDER, cell_size=80, font_size=11)


class TestIconItemInitialState:
    def test_app_initial_state_is_normal(self, app_icon):
        assert app_icon._state == IconItem.NORMAL

    def test_folder_initial_state_is_folder(self, folder_icon):
        assert folder_icon._state == IconItem.FOLDER

    def test_item_id(self, app_icon):
        assert app_icon.item_id == "app1"

    def test_bounding_rect_matches_cell(self, app_icon):
        r = app_icon.boundingRect()
        assert r.width() == 80
        assert r.height() == 80

    def test_size_matches_cell(self, app_icon):
        assert app_icon.size() == QSizeF(80, 80)


class TestIconItemStateTransitions:
    def test_set_state_selected(self, app_icon):
        app_icon.set_state(IconItem.SELECTED)
        assert app_icon._state == IconItem.SELECTED

    def test_set_state_drop_target(self, app_icon):
        app_icon.set_state(IconItem.DROP_TARGET)
        assert app_icon._state == IconItem.DROP_TARGET

    def test_set_state_ghost(self, app_icon):
        app_icon.set_state(IconItem.GHOST)
        assert app_icon._state == IconItem.GHOST

    def test_set_state_dragging(self, app_icon):
        app_icon.set_state(IconItem.DRAGGING)
        assert app_icon._state == IconItem.DRAGGING

    def test_set_state_back_to_normal(self, app_icon):
        app_icon.set_state(IconItem.SELECTED)
        app_icon.set_state(IconItem.NORMAL)
        assert app_icon._state == IconItem.NORMAL

    def test_all_state_constants_are_distinct(self):
        states = [
            IconItem.NORMAL,
            IconItem.FOLDER,
            IconItem.SELECTED,
            IconItem.DROP_TARGET,
            IconItem.GHOST,
            IconItem.DRAGGING,
        ]
        assert len(states) == len(set(states))


class TestIconItemSetItem:
    def test_set_item_updates_id(self, app_icon):
        new_item = {"id": "app2", "name": "Chrome", "type": "app"}
        app_icon.set_item(new_item)
        assert app_icon.item_id == "app2"

    def test_set_item_folder_updates_state(self, app_icon):
        app_icon.set_item(_FOLDER)
        assert app_icon._state == IconItem.FOLDER

    def test_set_item_app_resets_state_to_normal(self, folder_icon):
        folder_icon.set_item(_APP)
        assert folder_icon._state == IconItem.NORMAL


class TestIconItemCellResize:
    def test_set_cell_size_updates_bounding_rect(self, app_icon):
        app_icon.set_cell_size(120, 14)
        assert app_icon.boundingRect().width() == 120
        assert app_icon.boundingRect().height() == 120

    def test_set_cell_size_updates_size(self, app_icon):
        app_icon.set_cell_size(100, 12)
        assert app_icon.size() == QSizeF(100, 100)


class TestIconItemClickSignal:
    def test_click_emits_item_id(self, qapp, app_icon):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QGraphicsScene

        scene = QGraphicsScene()
        scene.addItem(app_icon)
        app_icon.setPos(0, 0)

        received = []
        app_icon.clicked.connect(received.append)

        app_icon._drag_start = QPointF(40, 40)

        class FakeEvent:
            def button(self):
                return Qt.MouseButton.LeftButton

            def pos(self):
                return QPointF(40, 40)

            def accept(self):
                pass

        app_icon.mouseReleaseEvent(FakeEvent())
        assert received == ["app1"]
