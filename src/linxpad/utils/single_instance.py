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

"""
Single-instance manager using a Unix domain socket.

First instance: binds the socket and listens for show signals.
Subsequent instances: connect to the socket, send "show", then exit.
"""

import logging
import os
import socket

from PyQt6.QtCore import QObject, QSocketNotifier, pyqtSignal

logger = logging.getLogger(__name__)

_SOCKET_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", os.path.expanduser("~/.config/linxpad")),
    "linxpad.sock",
)


class SingleInstance(QObject):
    show_requested = pyqtSignal()  # emitted when another instance asks to show
    rescan_requested = pyqtSignal()  # emitted when another instance asks to rescan

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server: socket.socket | None = None
        self._notifier: QSocketNotifier | None = None

    def is_primary(self) -> bool:
        """Try to become the primary instance. Returns True if we are primary."""
        # Clean up stale socket
        if os.path.exists(_SOCKET_PATH):
            try:
                # Try connecting — if it succeeds, another instance is running
                test = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test.connect(_SOCKET_PATH)
                test.sendall(b"show")
                test.close()
                return False  # another instance is running
            except (ConnectionRefusedError, OSError):
                os.unlink(_SOCKET_PATH)

        # Bind as primary
        try:
            self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server.bind(_SOCKET_PATH)
            self._server.listen(5)
            self._server.setblocking(False)
            self._notifier = QSocketNotifier(self._server.fileno(), QSocketNotifier.Type.Read, self)
            self._notifier.activated.connect(self._on_connection)
            return True
        except OSError:
            logger.exception("Failed to bind single-instance socket")
            return True  # fail open — let the app run

    def send_message(self, message: bytes) -> bool:
        """Send a message to the primary instance. Returns True if delivered."""
        if not os.path.exists(_SOCKET_PATH):
            return False
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(_SOCKET_PATH)
            sock.sendall(message)
            sock.close()
            return True
        except OSError:
            return False

    def _on_connection(self) -> None:
        try:
            conn, _ = self._server.accept()
            data = conn.recv(64)
            conn.close()
            if data == b"show":
                self.show_requested.emit()
            elif data == b"rescan":
                self.rescan_requested.emit()
        except OSError:
            pass

    def cleanup(self) -> None:
        if self._notifier:
            self._notifier.setEnabled(False)
        if self._server:
            self._server.close()
        if os.path.exists(_SOCKET_PATH):
            os.unlink(_SOCKET_PATH)
