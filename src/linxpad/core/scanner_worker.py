import logging

from PyQt6.QtCore import QThread, pyqtSignal

from ..services import DesktopScanner

logger = logging.getLogger(__name__)


class ScannerWorker(QThread):
    """Scans .desktop files in a background thread and emits results."""

    results_ready = pyqtSignal(list)  # List[dict]

    def __init__(self, scanner: DesktopScanner, parent=None):
        super().__init__(parent)
        self._scanner = scanner

    def run(self) -> None:
        try:
            results = self._scanner.scan()
            self.results_ready.emit(results)
        except Exception:
            logger.exception("Background scan failed")
            self.results_ready.emit([])
