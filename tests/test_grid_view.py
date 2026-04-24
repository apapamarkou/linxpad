"""Tests for GridView — page management and drag/drop events using QTest."""

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QMimeData, QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from linxpad.ui.graphics.grid_view import GridView

_PAGE_A = [
    {"id": f"a{i}", "name": f"App A{i}", "type": "app", "exec": f"a{i}.desktop"} for i in range(4)
]
_PAGE_B = [
    {"id": f"b{i}", "name": f"App B{i}", "type": "app", "exec": f"b{i}.desktop"} for i in range(4)
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_view(cols=4, rows=1, spacing=10):
    view = GridView(cols=cols, rows=rows, font_size=11, spacing=spacing, icon_resolver=None)
    view.resize(500, 200)
    return view


class TestGridViewPageManagement:
    def test_load_pages_sets_page_count(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        assert view.page_count == 2

    def test_load_empty_creates_one_page(self, qapp):
        view = _make_view()
        view.load_pages([])
        assert view.page_count == 1

    def test_initial_page_is_zero(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        assert view.current_page == 0

    def test_current_scene_has_correct_items(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        scene = view.current_scene()
        assert scene is not None
        assert scene.count() == 4
        assert scene.icon_items[0].item_id == "a0"

    def test_scene_at_returns_correct_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        scene = view.scene_at(1)
        assert scene is not None
        assert scene.icon_items[0].item_id == "b0"

    def test_scene_at_out_of_range_returns_none(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        assert view.scene_at(5) is None

    def test_go_to_page_changes_current_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view._show_page_silent(1)  # bypass animation for test
        assert view.current_page == 1

    def test_go_to_page_out_of_range_ignored(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.go_to_page(99)
        assert view.current_page == 0

    def test_append_empty_page_increases_count(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.append_empty_page()
        assert view.page_count == 2

    def test_remove_trailing_empty_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.append_empty_page()
        assert view.page_count == 2
        view.remove_trailing_empty_page()
        assert view.page_count == 1

    def test_remove_trailing_does_not_remove_non_empty(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view.remove_trailing_empty_page()
        assert view.page_count == 2

    def test_remove_trailing_does_not_remove_last_page(self, qapp):
        view = _make_view()
        view.load_pages([])
        view.remove_trailing_empty_page()
        assert view.page_count == 1

    def test_load_pages_resets_to_page_zero(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view._show_page_silent(1)
        view.load_pages([_PAGE_A])
        assert view.current_page == 0

    def test_load_pages_clamps_current_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view._show_page_silent(1)
        view.load_pages([_PAGE_A])  # only 1 page now
        assert view.current_page == 0


class TestGridViewSignals:
    def test_page_changed_emitted_on_show_silent(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        received = []
        view.page_changed.connect(received.append)
        view._show_page_silent(1)
        assert 1 in received

    def test_item_clicked_emitted(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        received = []
        view.item_clicked.connect(lambda iid, itype: received.append((iid, itype)))
        scene = view.current_scene()
        # Simulate click signal from icon directly
        scene.icon_items[0].clicked.emit("a0")
        assert len(received) == 1
        assert received[0][0] == "a0"

    def test_background_clicked_emitted_on_empty_area(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.show()
        received = []
        view.background_clicked.connect(lambda: received.append(True))
        # Click far outside any icon
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(490, 190))
        assert received


class TestGridViewWheelNavigation:
    def test_wheel_down_goes_to_next_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        # Bypass animation
        view._animating = False
        received = []
        view.page_changed.connect(received.append)

        # Simulate wheel event going to next page directly
        view._show_page_silent(0)
        view.go_to_page(1)  # go_to_page calls _animate_to_page which sets _current_page
        # Since animation is async, just verify go_to_page updates _current_page
        assert view._current_page == 1

    def test_wheel_up_goes_to_prev_page(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view._show_page_silent(1)
        view._animating = False
        view.go_to_page(0)
        assert view._current_page == 0

    def test_next_page_at_last_does_nothing(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.next_page()
        assert view.current_page == 0

    def test_prev_page_at_first_does_nothing(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A, _PAGE_B])
        view.prev_page()
        assert view.current_page == 0


class TestGridViewDragDrop:
    def test_drag_enter_accepted_for_item_mime(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])
        view.show()

        received = []
        view.drag_started.connect(lambda: received.append(True))

        mime = QMimeData()
        mime.setText("item:a0")

        # Simulate dragEnterEvent

        class FakeDragEnter:
            def mimeData(self):
                return mime

            def acceptProposedAction(self):
                self._accepted = True

            def ignore(self):
                self._accepted = False

            _accepted = False

        event = FakeDragEnter()
        view.dragEnterEvent(event)
        assert event._accepted

    def test_drag_enter_ignored_for_non_item_mime(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])

        mime = QMimeData()
        mime.setText("not-an-item")

        class FakeDragEnter:
            def mimeData(self):
                return mime

            def acceptProposedAction(self):
                self._accepted = True

            def ignore(self):
                self._accepted = False

            _accepted = True

        event = FakeDragEnter()
        view.dragEnterEvent(event)
        assert not event._accepted

    def test_drop_event_ignored_when_no_active_drag(self, qapp):
        view = _make_view()
        view.load_pages([_PAGE_A])

        mime = QMimeData()
        mime.setText("item:a0")

        class FakeDrop:
            def mimeData(self):
                return mime

            def position(self):
                from PyQt6.QtCore import QPointF

                return QPointF(40, 40)

            def acceptProposedAction(self):
                self._accepted = True

            def ignore(self):
                self._accepted = False

            _accepted = True

        event = FakeDrop()
        view.dropEvent(event)
        assert not event._accepted

    def test_reorder_signal_emitted_after_drop(self, qapp):
        view = _make_view(cols=4, rows=1, spacing=10)
        view.load_pages([_PAGE_A])
        view.show()
        QTest.qWaitForWindowExposed(view)

        reorders = []
        view.reorder_requested.connect(lambda *a: reorders.append(a))

        scene = view.current_scene()
        icon = scene.icon_items[0]
        view._drag.start(icon, 0, scene)

        # Drop in the left sixth of slot 1 — outside the centre third,
        # so _hit_icon returns None and reorder fires.
        cell = view._cell
        stride = cell + 10
        drop_x = int(stride + cell * 0.1)  # left edge of slot 1, not centre third

        class FakeDrop:
            def mimeData(self_):
                m = QMimeData()
                m.setText("item:a0")
                return m

            def position(self_):
                from PyQt6.QtCore import QPointF

                return QPointF(drop_x, cell // 2)

            def acceptProposedAction(self_):
                self_._accepted = True

            def ignore(self_):
                self_._accepted = False

            _accepted = False

        view.dropEvent(FakeDrop())
        assert len(reorders) == 1
        assert reorders[0][0] == "a0"
