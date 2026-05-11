#!/usr/bin/env python3
import logging
import sys

if __name__ == "__main__" and __package__ is None:
    import os

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    __package__ = "linxpad"

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .core import LauncherState, ScannerWorker
from .services import ConfigService, DesktopScanner, DesktopWatcher, IconResolver, UISettings
from .ui import LauncherWindow
from .utils import SingleInstance

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def _rescan() -> None:
    icons = IconResolver()
    scanner = DesktopScanner(icons)
    config = ConfigService()
    state = LauncherState(config, scanner, icons)
    state.load()
    results = scanner.scan()
    changed = state.apply_scan_results(results)
    if changed:
        si = SingleInstance()
        si.send_message(b"rescan")


def main() -> None:
    if "--rescan" in sys.argv:
        _rescan()
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    instance = SingleInstance()
    if not instance.is_primary():
        sys.exit(0)

    icons = IconResolver()
    scanner = DesktopScanner(icons)
    config = ConfigService()
    settings = UISettings()
    state = LauncherState(config, scanner, icons, page_size=settings.cols * settings.rows)

    state.load()
    if state.is_first_run():
        state.apply_scan_results(scanner.scan())

    worker = ScannerWorker(scanner)
    window = LauncherWindow(state, worker, settings)
    window.show()

    instance.show_requested.connect(window.show_window)
    instance.rescan_requested.connect(window.trigger_rescan)

    # DesktopWatcher fires from a watchdog background thread.
    # QTimer.singleShot marshals the call onto the Qt main thread,
    # which then starts the ScannerWorker QThread — keeping the UI
    # fully responsive during the scan.
    watcher = DesktopWatcher(on_changed=lambda: QTimer.singleShot(0, window.trigger_rescan))
    watcher.start()

    app.aboutToQuit.connect(watcher.stop)
    app.aboutToQuit.connect(instance.cleanup)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
