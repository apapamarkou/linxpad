"""LauncherWindow — thin coordinator.

Responsibilities:
- Build and wire all UI components
- Handle keyboard events
- Delegate all business logic to LauncherState
- Delegate all grid rendering to GridView
- No drag logic, no layout math
"""

from __future__ import annotations

import os
import pathlib
import subprocess

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import LauncherState, ScannerWorker
from ..services import UISettings
from .components import InlineTitle
from .graphics import DotsIndicator, GridView
from .services import SearchService
from .settings_view import SettingsView
from .theme import (
    FLIP_ZONE_HOT,
    FLIP_ZONE_IDLE,
    LABEL_IDLE,
    MAIN_STYLESHEET,
    TITLE_LABEL,
)
from .views.folder_view import FolderView
from .views.search_view import SearchView


class _Nav:
    """Tracks navigation state (folder / page)."""

    def __init__(self):
        self.in_folder = False
        self.folder_id: str | None = None
        self.current_page: int = 0

    def enter_folder(self, folder_id: str) -> None:
        self.in_folder = True
        self.folder_id = folder_id

    def exit_folder(self) -> None:
        self.in_folder = False
        self.folder_id = None


class LauncherWindow(QMainWindow):

    def __init__(self, state: LauncherState, worker: ScannerWorker, settings: UISettings):
        super().__init__()
        self.state = state
        self._worker = worker
        self._settings = settings
        self._nav = _Nav()
        self._selected = 0
        self._search_service = SearchService(state)

        self._setup_icon_theme()
        self._build_ui()
        self.refresh_display()
        self.setFocus()

        self._worker.results_ready.connect(self._on_scan_done)
        self._worker.start()

    # ── rescan ────────────────────────────────────────────────────────────────

    def trigger_rescan(self) -> None:
        """Start a background rescan if one is not already running."""
        if not self._worker.isRunning():
            self._worker.start()

    # ── icon theme ────────────────────────────────────────────────────────────

    @staticmethod
    def _setup_icon_theme() -> None:
        paths = list(QIcon.themeSearchPaths())
        for p in [
            "/usr/share/icons",
            "/usr/share/pixmaps",
            os.path.expanduser("~/.local/share/icons"),
        ]:
            if p not in paths and pathlib.Path(p).exists():
                paths.append(p)
        root = pathlib.Path("/usr/share/icons")
        if root.exists():
            for sub in root.iterdir():
                if sub.is_dir() and str(sub) not in paths:
                    paths.append(str(sub))
        QIcon.setThemeSearchPaths(paths)
        try:
            QIcon.setThemeName("breeze-dark")
        except Exception:
            pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("LinxPad")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.setWindowOpacity(self._settings.opacity)
        self.setStyleSheet(MAIN_STYLESHEET)

        screen = QApplication.primaryScreen().geometry()
        if self._settings.fullscreen:
            self.showFullScreen()
        else:
            self.setGeometry(screen)
            self.show()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(100, 50, 100, 50)
        root.setSpacing(20)

        root.addWidget(self._build_header())
        root.addWidget(self._build_search_bar())

        # Pages stack: grid | folder | search
        self._grid_view = GridView(
            cols=self._settings.cols,
            rows=self._settings.rows,
            font_size=self._settings.font_size,
            spacing=self._settings.spacing,
            icon_resolver=self.state.icons,
        )
        self._grid_view.item_clicked.connect(self._on_grid_item_clicked)
        self._grid_view.reorder_requested.connect(self._on_reorder)
        self._grid_view.button_drop_requested.connect(self._on_button_drop)
        self._grid_view.move_to_page_requested.connect(self._on_move_to_page)
        self._grid_view.move_to_slot_requested.connect(self._on_move_to_slot)
        self._grid_view.page_changed.connect(self._on_page_changed)
        self._grid_view.drag_started.connect(self._show_flip_zones)
        self._grid_view.drag_ended.connect(self._hide_flip_zones)
        self._grid_view.background_clicked.connect(self._on_background_click)
        self._dots = DotsIndicator()
        self._dots.page_requested.connect(self._grid_view.go_to_page)
        self._grid_view.anim_started.connect(lambda: self._grid_view.setScene(QGraphicsScene()))
        self._grid_view.anim_ended.connect(lambda: None)

        grid_container = QWidget()
        gc_layout = QVBoxLayout(grid_container)
        gc_layout.setContentsMargins(0, 0, 0, 0)
        gc_layout.setSpacing(0)
        gc_layout.addWidget(self._grid_view)
        gc_layout.addWidget(self._dots, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._folder_view = FolderView(
            cols=self._settings.cols,
            font_size=self._settings.font_size,
            spacing=self._settings.spacing,
            icon_resolver=self.state.icons,
        )
        self._folder_view.item_clicked.connect(self._on_folder_item_clicked)
        self._folder_view.reorder_requested.connect(self._on_folder_reorder)
        self._folder_view.background_clicked.connect(self._on_folder_background_click)

        self._search_view = SearchView(
            search_service=self._search_service,
            icon_resolver=self.state.icons,
            hide_fn=self._hide_self,
        )

        self._pages = QStackedWidget()
        self._pages.addWidget(grid_container)
        self._pages.addWidget(self._folder_view)
        self._pages.addWidget(self._search_view)
        root.addWidget(self._pages)

        self._flip_left = self._make_flip_zone(-1, central)
        self._flip_right = self._make_flip_zone(+1, central)
        self._reposition_flip_zones()

        self._overlay_drop = self._make_overlay("⬆  Drop to remove from folder", central)
        self._overlay_hint = self._make_overlay(
            "⧖  Drop onto another app to create a folder", central
        )

        central.resizeEvent = lambda e: self._on_central_resize()

    def _build_header(self) -> QWidget:
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)

        self._static_title = QLabel("Applications")
        self._static_title.setStyleSheet(TITLE_LABEL)

        self._inline_title = InlineTitle()
        self._inline_title.hide()

        gear = QLabel("⚙")
        gear.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 22px; background: transparent;"
            "padding: 4px 8px; border-radius: 8px;"
        )
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.mousePressEvent = lambda _e: self._open_settings()

        hl.addWidget(self._static_title)
        hl.addWidget(self._inline_title)
        hl.addStretch()
        hl.addWidget(gear)
        return header

    def _build_search_bar(self) -> QWidget:
        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search applications…")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(lambda: self._on_search(self._search.text()))
        self._search.textChanged.connect(lambda _: self._search_timer.start())
        self._search.setMaximumWidth(600)
        wrapper = QWidget()
        QVBoxLayout(wrapper).addWidget(self._search, alignment=Qt.AlignmentFlag.AlignCenter)
        return wrapper

    @staticmethod
    def _make_overlay(text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(LABEL_IDLE)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label.hide()
        return label

    def _make_flip_zone(self, direction: int, central: QWidget) -> QLabel:
        label = QLabel("◀" if direction < 0 else "▶", central)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        label.setAcceptDrops(True)
        label.hide()

        timer = QTimer(label)
        timer.setSingleShot(True)
        timer.setInterval(600)

        def _drag_enter(event):
            if not (event.mimeData().hasText() and event.mimeData().text().startswith("item:")):
                event.ignore()
                return
            src_id = event.mimeData().text().replace("item:", "")
            if direction < 0 and self._grid_view.current_page > 0:
                label.setStyleSheet(FLIP_ZONE_HOT)
                timer.start()
                event.acceptProposedAction()
                return
            if direction > 0:
                if self._grid_view.current_page < self._grid_view.page_count - 1:
                    label.setStyleSheet(FLIP_ZONE_HOT)
                    timer.start()
                    event.acceptProposedAction()
                    return
                pages = self.state.get_main_items_by_page()
                last = pages[-1] if pages else []
                if [it for it in last if it["id"] != src_id]:
                    label.setText("+")
                    label.setStyleSheet(FLIP_ZONE_HOT)
                    event.acceptProposedAction()
                    return
            event.ignore()

        def _drag_leave(event):
            timer.stop()
            label.setText("▶" if direction > 0 else "◀")
            label.setStyleSheet(FLIP_ZONE_IDLE)
            if direction > 0:
                self._grid_view.remove_trailing_empty_page()

        def _drop(event):
            timer.stop()
            label.setText("▶" if direction > 0 else "◀")
            label.setStyleSheet(FLIP_ZONE_IDLE)
            if not (event.mimeData().hasText() and event.mimeData().text().startswith("item:")):
                event.ignore()
                return
            src_id = event.mimeData().text().replace("item:", "")
            is_new_page = (
                direction > 0 and self._grid_view.current_page == self._grid_view.page_count - 1
            )
            if is_new_page:
                target_page = self._grid_view.page_count
                moved = self.state.move_to_first_empty_slot(src_id, target_page)
                if moved:
                    self._nav.current_page = target_page
                self._hide_flip_zones()
                self.refresh_display()
                event.acceptProposedAction()
                return
            target_page = (
                self._grid_view.current_page - 1
                if direction < 0
                else self._grid_view.current_page + 1
            )
            target_page = max(0, min(target_page, self._grid_view.page_count - 1))
            moved = self.state.move_to_first_empty_slot(src_id, target_page)
            if moved:
                self._nav.current_page = target_page
            else:
                self._grid_view.remove_trailing_empty_page()
            self._hide_flip_zones()
            self.refresh_display()
            event.acceptProposedAction()

        def _flip():
            if direction < 0:
                self._grid_view.prev_page()
            else:
                self._grid_view.next_page()
            self._nav.current_page = self._grid_view.current_page

        timer.timeout.connect(_flip)
        label.dragEnterEvent = _drag_enter
        label.dragLeaveEvent = _drag_leave
        label.dragMoveEvent = lambda e: e.acceptProposedAction()
        label.dropEvent = _drop
        return label

    # ── layout helpers ────────────────────────────────────────────────────────

    def _on_central_resize(self) -> None:
        self._reposition_flip_zones()
        self._reposition_overlays()

    def _reposition_flip_zones(self) -> None:
        central = self.centralWidget()
        if not central:
            return
        h = central.height()
        w = 100
        self._flip_left.setGeometry(0, 0, w, h)
        self._flip_right.setGeometry(central.width() - w, 0, w, h)

    def _reposition_overlays(self) -> None:
        geo = self._pages.geometry()
        w, h = 480, 80
        for label in (self._overlay_drop, self._overlay_hint):
            label.setGeometry(
                geo.x() + (geo.width() - w) // 2,
                geo.y() + (geo.height() - h) // 2,
                w,
                h,
            )

    def _show_flip_zones(self) -> None:
        self._reposition_flip_zones()
        self._flip_left.show()
        self._flip_right.show()
        self._flip_left.raise_()
        self._flip_right.raise_()

    def _hide_flip_zones(self) -> None:
        self._flip_left.hide()
        self._flip_right.hide()
        self._grid_view.remove_trailing_empty_page()

    # ── navigation ────────────────────────────────────────────────────────────

    def _show_grid(self) -> None:
        if self._nav.in_folder:
            self._slide_pages(self._pages.widget(0), self._folder_view, direction=1)
        else:
            self._slide_pages(self._folder_view, self._pages.widget(0), direction=-1)

    def _show_search(self) -> None:
        self._pages.setCurrentWidget(self._search_view)

    def _slide_pages(self, outgoing: QWidget, incoming: QWidget, direction: int) -> None:
        if self._pages.currentWidget() is incoming:
            return
        h = self._pages.height()
        incoming.setGeometry(0, direction * h, self._pages.width(), h)
        self._pages.setCurrentWidget(incoming)
        incoming.show()
        incoming.raise_()

        anim_out = QPropertyAnimation(outgoing, b"pos", self)
        anim_out.setDuration(280)
        anim_out.setStartValue(QPoint(0, 0))
        anim_out.setEndValue(QPoint(0, -direction * h))
        anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim_in = QPropertyAnimation(incoming, b"pos", self)
        anim_in.setDuration(280)
        anim_in.setStartValue(QPoint(0, direction * h))
        anim_in.setEndValue(QPoint(0, 0))
        anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        anim_in.finished.connect(lambda: outgoing.move(0, 0))
        anim_out.start()
        anim_in.start()

    # ── display ───────────────────────────────────────────────────────────────

    def refresh_display(self) -> None:
        self._update_header()
        if self._nav.in_folder and self._nav.folder_id:
            items = self.state.get_folder_items(self._nav.folder_id)
            self._folder_view.load_items(items, self._grid_view._cell or 80)
        else:
            pages = self.state.get_main_items_by_page()
            self._grid_view.load_pages(pages)
            self._dots.set_count(self._grid_view.page_count)
            self._dots.set_active(self._nav.current_page)
        self._show_grid()

    def _update_header(self) -> None:
        if self._nav.in_folder and self._nav.folder_id:
            folder = self.state.folders.get(self._nav.folder_id)
            self._inline_title.set_text(folder.name if folder else "Folder")
            self._static_title.hide()
            self._inline_title.show()
        else:
            self._inline_title.hide()
            self._static_title.show()

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_grid_item_clicked(self, item_id: str, item_type: str) -> None:
        if item_type == "folder":
            self._nav.enter_folder(item_id)
            self._search.clear()
            self.refresh_display()
        else:
            try:
                subprocess.Popen(["gtk-launch", self.state.apps[item_id].exec])
            except Exception:
                pass
            self._hide_self()

    def _on_folder_item_clicked(self, item_id: str, item_type: str) -> None:
        if item_type == "folder":
            self._nav.enter_folder(item_id)
            self.refresh_display()
        else:
            try:
                subprocess.Popen(["gtk-launch", self.state.apps[item_id].exec])
            except Exception:
                pass
            self._hide_self()

    def _on_folder_reorder(self, dragged_id: str, target_id: str, placement: str) -> None:
        self.state.reorder(dragged_id, target_id, placement, True, self._nav.folder_id)
        self.refresh_display()

    def _on_folder_background_click(self) -> None:
        self._nav.exit_folder()
        self.refresh_display()

    def _on_page_changed(self, page: int) -> None:
        self._nav.current_page = page
        self._dots.set_active(page)

    def _on_reorder(self, dragged_id: str, target_id: str, placement: str) -> None:
        self.state.reorder(
            dragged_id, target_id, placement, self._nav.in_folder, self._nav.folder_id
        )
        self._nav.current_page = self._grid_view.current_page
        self.refresh_display()

    def _on_move_to_page(self, item_id: str, page: int) -> None:
        self.state.move_to_page(item_id, page)
        self._nav.current_page = page
        self.refresh_display()

    def _on_move_to_slot(self, item_id: str, page: int) -> None:
        self.state.move_to_first_empty_slot(item_id, page)
        self._nav.current_page = page
        self.refresh_display()

    def _on_button_drop(self, src_id: str, dst_id: str, dst_type: str) -> None:
        src_type = "app" if src_id in self.state.apps else None
        if dst_type == "folder" and src_type == "app":
            self.state.add_to_folder(dst_id, src_id)
        elif dst_type == "app" and src_type == "app":
            self.state.create_folder(dst_id, src_id)
        self.refresh_display()

    def _on_scan_done(self, results: list) -> None:
        if self.state.apply_scan_results(results) and not self._search.text():
            self.refresh_display()

    def _on_search(self, text: str) -> None:
        self._selected = 0
        if text.strip():
            self._static_title.show()
            self._static_title.setText("Search Results")
            self._inline_title.hide()
            self._search_view.set_query(text.strip().lower())
            self._show_search()
        else:
            self._search_view.cancel_web_search()
            self._static_title.setText("Applications")
            self.refresh_display()

    # ── settings ──────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        if not hasattr(self, "_settings_view"):
            self._settings_view = SettingsView(self._settings, self.centralWidget())
            self._settings_view.closed.connect(self._on_settings_closed)
        self._settings_view.setGeometry(self.centralWidget().rect())
        self._settings_view.show()
        self._settings_view.raise_()
        self._settings_view.setFocus()
        panel = self._settings_view._panel
        geo = panel.geometry()
        start = geo.translated(0, -geo.height())
        anim = QPropertyAnimation(panel, b"geometry", self._settings_view)
        anim.setDuration(220)
        anim.setStartValue(start)
        anim.setEndValue(geo)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

    def _on_settings_closed(
        self, cols: int, rows: int, spacing: int, transp: int, keep: bool
    ) -> None:
        import os
        import sys

        s = self._settings
        s._values["cols"] = str(cols)
        s._values["rows"] = str(rows)
        s._values["spacing"] = str(spacing)
        s._values["transparency"] = str(transp)
        s._values["keep-previous-state"] = "yes" if keep else "no"
        s.save()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ── hide self ─────────────────────────────────────────────────────────────

    def _hide_self(self) -> None:
        if not self._settings.keep_previous_state and self._search.text():
            self._search.blockSignals(True)
            self._search.clear()
            self._search.blockSignals(False)
            self._search_view.cancel_web_search()
            self._static_title.setText("Applications")
            self.refresh_display()
        self.hide()

    # ── public API ────────────────────────────────────────────────────────────

    def show_window(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        if self._settings.fullscreen:
            self.showFullScreen()
        else:
            self.setGeometry(screen)
            self.show()
        if self._search.text().strip():
            self._show_search()
        else:
            self._show_grid()
            self.setFocus()
        self.raise_()
        self.activateWindow()

    # ── keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self._handle_escape()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._handle_enter()
        elif key == Qt.Key.Key_Tab:
            (self.setFocus if self._search.hasFocus() else self._search.setFocus)()
        elif key == Qt.Key.Key_PageUp and not self._nav.in_folder and not self._search.text():
            self._grid_view.prev_page()
        elif key == Qt.Key.Key_PageDown and not self._nav.in_folder and not self._search.text():
            self._grid_view.next_page()
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self._search.text():
            rows = self._search_view.rows
            if rows:
                sel = self._search_view.selected
                sel = min(sel + 1, len(rows) - 1) if key == Qt.Key.Key_Down else max(sel - 1, 0)
                self._search_view.highlight(sel)
        elif (
            key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down)
            and not self._search.hasFocus()
        ):
            self._handle_arrow(key)
        elif not self._search.hasFocus() and event.text().isprintable() and event.text():
            self._search.setFocus()
            self._search.setText(self._search.text() + event.text())
        else:
            super().keyPressEvent(event)

    def _handle_escape(self) -> None:
        if self._search.text():
            self._search.clear()
        elif self._nav.in_folder:
            self._nav.exit_folder()
            self.refresh_display()
        else:
            self.hide()

    def _handle_enter(self) -> None:
        if self._search.text():
            rows = self._search_view.rows
            if rows:
                rows[self._search_view.selected]._on_click()
            else:
                self._search_view.launch_first()
            return
        scene = self._grid_view.current_scene()
        if scene is None:
            return
        icons = [it for it in scene.icon_items if it._state not in ("ghost", "dragging")]
        if not icons:
            return
        icon = icons[max(0, min(self._selected, len(icons) - 1))]
        self._on_grid_item_clicked(icon.item_id, icon.item.get("type", "app"))

    def _handle_arrow(self, key) -> None:
        scene = self._grid_view.current_scene()
        if scene is None:
            return
        icons = [it for it in scene.icon_items if it._state not in ("ghost", "dragging")]
        count = len(icons)
        if count == 0:
            return
        cols = self._settings.cols
        rel = max(0, min(self._selected, count - 1))
        if key == Qt.Key.Key_Right:
            rel = (rel + 1) % count
        elif key == Qt.Key.Key_Left:
            rel = (rel - 1) % count
        elif key == Qt.Key.Key_Down:
            new = rel + cols
            rel = new if new < count else rel
        elif key == Qt.Key.Key_Up:
            new = rel - cols
            rel = new if new >= 0 else rel
        self._selected = rel
        for i, icon in enumerate(icons):
            if i == rel:
                icon.set_state("selected")
            else:
                icon.set_state("folder" if icon.item.get("type") == "folder" else "normal")

    # ── mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        w = QApplication.widgetAt(QCursor.pos())
        while w:
            if w is self._search:
                super().mousePressEvent(event)
                return
            if w is self._inline_title and self._nav.in_folder and self._nav.folder_id:
                self._inline_title.start_edit(self._on_folder_rename)
                return
            if w is self._grid_view or w is self._folder_view:
                super().mousePressEvent(event)
                return
            w = w.parent()
        self._on_background_click()

    def _on_background_click(self) -> None:
        if self._search.text():
            self._search.clear()
        elif self._nav.in_folder:
            self._nav.exit_folder()
            self.refresh_display()
        else:
            self.hide()

    def _on_folder_rename(self, name: str) -> None:
        if self._nav.folder_id and name:
            self.state.rename_folder(self._nav.folder_id, name)
            self._inline_title.set_text(name)

    # ── window drag/drop (remove from folder) ─────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if self._nav.in_folder and event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._nav.in_folder:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        if self._nav.in_folder and event.mimeData().hasText():
            item_id = event.mimeData().text().replace("item:", "")
            deleted = self.state.remove_from_folder(item_id)
            if deleted and deleted == self._nav.folder_id:
                self._nav.exit_folder()
            self.refresh_display()
            event.acceptProposedAction()
        else:
            event.ignore()
