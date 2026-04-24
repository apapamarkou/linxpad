"""DesktopWatcher — watches .desktop file directories and calls a callback on changes.

Watches:
- /usr/share/applications/
- ~/.local/share/applications/

Calls on_changed() when any .desktop file is created, deleted, or modified.
Debounces rapid bursts with a configurable delay.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_WATCH_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]

_DEBOUNCE_SECONDS = 3.0


class _Handler(FileSystemEventHandler):
    def __init__(self, on_changed: Callable[[], None]) -> None:
        super().__init__()
        self._on_changed = on_changed
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _is_desktop(self, path: str) -> bool:
        return path.endswith(".desktop")

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(_DEBOUNCE_SECONDS, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._on_changed()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_desktop(str(event.src_path)):
            self._schedule()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_desktop(str(event.src_path)):
            self._schedule()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_desktop(str(event.src_path)):
            self._schedule()

    def on_moved(self, event: FileSystemEvent) -> None:
        src = self._is_desktop(str(event.src_path))
        dst = self._is_desktop(str(event.dest_path))
        if not event.is_directory and (src or dst):
            self._schedule()


class DesktopWatcher:
    """Watches application directories for .desktop file changes."""

    def __init__(self, on_changed: Callable[[], None]) -> None:
        self._on_changed = on_changed
        self._observer: Observer | None = None

    def start(self) -> None:
        self._observer = Observer()
        handler = _Handler(self._on_changed)
        for path in _WATCH_DIRS:
            if os.path.isdir(path):
                self._observer.schedule(handler, path, recursive=False)
                logger.debug("Watching %s", path)
            else:
                logger.debug("Skipping missing directory %s", path)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
