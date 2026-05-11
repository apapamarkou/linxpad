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
 
from PyQt6.QtCore import QTimer

from ...services import WebSearchWorker, search_home


class SearchService:
    """Computes search results from a query; UI only renders what this returns."""

    def __init__(self, state):
        self._state = state

    def app_results(self, query: str) -> list[dict]:
        return sorted(
            [
                {**a.to_dict(), "type": "app"}
                for a in self._state.apps.values()
                if query in a.name.lower() or query in (a.comment or "").lower()
            ],
            key=lambda x: x["name"].lower(),
        )

    def file_results(self, query: str) -> list[dict]:
        return list(search_home(query))

    @staticmethod
    def needs_web_search(query: str) -> bool:
        return len(query) > 8


class WebSearchController:
    """Owns the debounce timer and WebSearchWorker; decoupled from the window."""

    DELAY_MS = 1500

    def __init__(self, on_results):
        """on_results(results: list) called when search completes."""
        self._on_results = on_results
        self._worker: WebSearchWorker | None = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._run)
        self._pending: str = ""

    def search(self, query: str) -> None:
        self._pending = query
        self._timer.start(self.DELAY_MS)

    def cancel(self) -> None:
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.quit()

    def _run(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
        self._worker = WebSearchWorker(self._pending)
        self._worker.results_ready.connect(self._on_results)
        self._worker.start()
