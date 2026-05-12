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
