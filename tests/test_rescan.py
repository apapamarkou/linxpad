"""Tests for the linxpad --rescan headless entry point."""

import sys
from unittest.mock import patch

import pytest

import linxpad.main  # noqa: F401 — registers submodule for patch()


def _run_rescan(changed: bool = True):
    with (
        patch("linxpad.main.IconResolver"),
        patch("linxpad.main.DesktopScanner") as MockScanner,
        patch("linxpad.main.ConfigService"),
        patch("linxpad.main.LauncherState") as MockState,
        patch("linxpad.main.SingleInstance") as MockSI,
    ):
        mock_scanner = MockScanner.return_value
        mock_scanner.scan.return_value = [
            {"name": "Firefox", "exec": "firefox.desktop", "icon": None, "icon_name": "firefox"}
        ]
        mock_state = MockState.return_value
        mock_state.apply_scan_results.return_value = changed
        mock_si = MockSI.return_value

        from linxpad.main import _rescan

        _rescan()
        return mock_state, mock_scanner, mock_si


def test_rescan_calls_load_scan_apply():
    mock_state, mock_scanner, _ = _run_rescan()
    mock_state.load.assert_called_once()
    mock_scanner.scan.assert_called_once()
    mock_state.apply_scan_results.assert_called_once_with(mock_scanner.scan.return_value)


def test_rescan_notifies_instance_when_changed():
    _, _, mock_si = _run_rescan(changed=True)
    mock_si.send_message.assert_called_once_with(b"rescan")


def test_rescan_does_not_notify_when_unchanged():
    _, _, mock_si = _run_rescan(changed=False)
    mock_si.send_message.assert_not_called()


def test_main_rescan_flag_does_not_start_qt(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["linxpad", "--rescan"])
    with (
        patch("linxpad.main._rescan") as mock_rescan,
        patch("linxpad.main.QApplication") as MockQt,
    ):
        from linxpad.main import main

        main()
        mock_rescan.assert_called_once()
        MockQt.assert_not_called()


def test_main_no_rescan_flag_starts_qt(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["linxpad"])
    with (
        patch("linxpad.main.QApplication") as MockQt,
        patch("linxpad.main.SingleInstance") as MockSI,
        patch("linxpad.main.IconResolver"),
        patch("linxpad.main.DesktopScanner"),
        patch("linxpad.main.ConfigService"),
        patch("linxpad.main.UISettings"),
        patch("linxpad.main.LauncherState"),
        patch("linxpad.main.ScannerWorker"),
        patch("linxpad.main.LauncherWindow"),
    ):
        MockSI.return_value.is_primary.return_value = False
        with pytest.raises(SystemExit):
            from linxpad.main import main

            main()
        MockQt.assert_called_once()
