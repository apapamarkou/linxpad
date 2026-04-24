import subprocess
import urllib.parse

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..components import FileRow, SearchRow, SectionHeader, WebResultRow, WebSearchRow
from ..services import SearchService, WebSearchController
from ..theme import ROW_NORMAL, ROW_SELECTED


def _open(cmd: list) -> None:
    try:
        subprocess.Popen(cmd)
    except Exception:
        pass


class SearchView(QScrollArea):
    """Renders search results. Call set_query() to drive the full search flow."""

    def __init__(self, search_service: SearchService, icon_resolver, hide_fn):
        super().__init__()
        self._service = search_service
        self._icon_resolver = icon_resolver
        self._hide = hide_fn
        self._web = WebSearchController(on_results=self._apply_web_results)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setSpacing(4)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.addStretch()
        self.setWidget(self._container)

        self.rows: list = []
        self.selected: int = 0
        self._web_header: SectionHeader | None = None

    # ── public ───────────────────────────────────────────────────────────────

    def set_query(self, query: str) -> None:
        self._web.cancel()
        self._clear()
        app_results = self._service.app_results(query)
        file_results = self._service.file_results(query)
        self._render(app_results, file_results, query)
        if SearchService.needs_web_search(query):
            self._web.search(query)

    def cancel_web_search(self) -> None:
        self._web.cancel()

    def highlight(self, index: int) -> None:
        for i, row in enumerate(self.rows):
            row.setStyleSheet(ROW_SELECTED if i == index else ROW_NORMAL)
        self.selected = index
        if 0 <= index < len(self.rows):
            self.ensureWidgetVisible(self.rows[index])

    def launch_first(self) -> None:
        if self.rows:
            self.rows[0]._on_click()

    # ── private rendering ────────────────────────────────────────────────────

    def _render(self, app_results, file_results, query: str) -> None:
        if app_results:
            self._insert(SectionHeader("APPLICATIONS"))
            for app in app_results:
                row = SearchRow(app, self._make_app_launcher(app), self._icon_resolver)
                self._insert(row)
                self.rows.append(row)

        if file_results:
            self._insert(SectionHeader("FILE SYSTEM"))
            for item in file_results:
                row = FileRow(item, self._make_file_opener(item["path"]))
                self._insert(row)
                self.rows.append(row)

        if len(query) > 8:
            self._insert(SectionHeader("WEB SEARCH"))
            web_row = WebSearchRow(query, self._make_web_opener(query))
            self._insert(web_row)
            self.rows.append(web_row)
            self._web_header = SectionHeader("WEB RESULTS  ·  searching…")
            self._insert(self._web_header)

    def _apply_web_results(self, results: list) -> None:
        if self._web_header is None:
            return
        count = len(results)
        self._web_header.set_text(
            f"WEB RESULTS  ·  {count} found" if count else "WEB RESULTS  ·  no results"
        )
        if not results:
            return
        idx = self._vbox.indexOf(self._web_header)
        for i, result in enumerate(results):
            row = WebResultRow(result, self._make_url_opener(result["url"]))
            self._vbox.insertWidget(idx + 1 + i, row)
            self.rows.append(row)

    def _clear(self) -> None:
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows = []
        self.selected = 0
        self._web_header = None

    def _insert(self, widget: QWidget) -> None:
        self._vbox.insertWidget(self._vbox.count() - 1, widget)

    # ── action factories ─────────────────────────────────────────────────────

    def _make_app_launcher(self, app: dict):
        def _launch():
            _open(["gtk-launch", app["exec"]])
            self._hide()

        return _launch

    def _make_file_opener(self, path: str):
        def _open_file():
            _open(["xdg-open", path])
            self._hide()

        return _open_file

    def _make_web_opener(self, query: str):
        def _open_web():
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            _open(["xdg-open", url])
            self._hide()

        return _open_web

    def _make_url_opener(self, url: str):
        def _open_url():
            _open(["xdg-open", url])
            self._hide()

        return _open_url
