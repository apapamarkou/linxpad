"""Tests for DesktopWatcher."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from linxpad.services.desktop_watcher import _WATCH_DIRS, DesktopWatcher, _Handler

# ── _Handler debounce tests ───────────────────────────────────────────────────


class TestHandler:
    def test_desktop_file_created_triggers_callback(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=False, src_path="/usr/share/applications/foo.desktop")
        handler.on_created(event)
        time.sleep(0.1)
        # timer is pending — callback not yet called
        assert cb.call_count == 0
        # wait for debounce
        time.sleep(3.5)
        cb.assert_called_once()

    def test_non_desktop_file_ignored(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=False, src_path="/usr/share/applications/foo.txt")
        handler.on_created(event)
        time.sleep(3.5)
        cb.assert_not_called()

    def test_directory_event_ignored(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=True, src_path="/usr/share/applications/subdir")
        handler.on_created(event)
        time.sleep(3.5)
        cb.assert_not_called()

    def test_rapid_events_debounced_to_single_call(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=False, src_path="/usr/share/applications/foo.desktop")
        for _ in range(5):
            handler.on_created(event)
            time.sleep(0.1)
        time.sleep(3.5)
        cb.assert_called_once()

    def test_deleted_triggers_callback(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=False, src_path="/usr/share/applications/foo.desktop")
        handler.on_deleted(event)
        time.sleep(3.5)
        cb.assert_called_once()

    def test_modified_triggers_callback(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(is_directory=False, src_path="/usr/share/applications/foo.desktop")
        handler.on_modified(event)
        time.sleep(3.5)
        cb.assert_called_once()

    def test_moved_to_desktop_triggers_callback(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(
            is_directory=False,
            src_path="/tmp/foo.txt",
            dest_path="/usr/share/applications/foo.desktop",
        )
        handler.on_moved(event)
        time.sleep(3.5)
        cb.assert_called_once()

    def test_moved_non_desktop_ignored(self):
        cb = MagicMock()
        handler = _Handler(cb)
        event = MagicMock(
            is_directory=False,
            src_path="/tmp/foo.txt",
            dest_path="/usr/share/applications/foo.txt",
        )
        handler.on_moved(event)
        time.sleep(3.5)
        cb.assert_not_called()


# ── DesktopWatcher start/stop tests ──────────────────────────────────────────


class TestDesktopWatcher:
    def test_start_schedules_existing_dirs(self):
        cb = MagicMock()
        watcher = DesktopWatcher(on_changed=cb)
        with patch("linxpad.services.desktop_watcher.Observer") as MockObserver:
            mock_obs = MockObserver.return_value
            with patch("linxpad.services.desktop_watcher.os.path.isdir", return_value=True):
                watcher.start()
            assert mock_obs.schedule.call_count == len(_WATCH_DIRS)
            mock_obs.start.assert_called_once()

    def test_start_skips_missing_dirs(self):
        cb = MagicMock()
        watcher = DesktopWatcher(on_changed=cb)
        with patch("linxpad.services.desktop_watcher.Observer") as MockObserver:
            mock_obs = MockObserver.return_value
            with patch("linxpad.services.desktop_watcher.os.path.isdir", return_value=False):
                watcher.start()
            mock_obs.schedule.assert_not_called()
            mock_obs.start.assert_called_once()

    def test_stop_joins_observer(self):
        cb = MagicMock()
        watcher = DesktopWatcher(on_changed=cb)
        with patch("linxpad.services.desktop_watcher.Observer") as MockObserver:
            mock_obs = MockObserver.return_value
            with patch("linxpad.services.desktop_watcher.os.path.isdir", return_value=True):
                watcher.start()
            watcher.stop()
            mock_obs.stop.assert_called_once()
            mock_obs.join.assert_called_once()
            assert watcher._observer is None

    def test_stop_before_start_is_safe(self):
        cb = MagicMock()
        watcher = DesktopWatcher(on_changed=cb)
        watcher.stop()  # should not raise
