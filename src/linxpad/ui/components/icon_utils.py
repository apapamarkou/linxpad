"""Icon loading utilities — no Qt widgets, only QPixmap / QIcon."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def make_pixmap(path: str, size: int) -> QPixmap:
    return QPixmap(path).scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _fallback(size: int, letter: str) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor("#2d2d2d"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#ffffff"))
    f = QFont()
    f.setBold(True)
    f.setPointSize(max(8, int(size * 0.4)))
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return pix


def load_app_icon(label, item: dict, size: int, icon_resolver=None) -> None:
    """Load an app icon into a QLabel with fallback chain."""
    icon_path = item.get("icon")
    icon_name = item.get("icon_name")

    if icon_path and os.path.exists(icon_path):
        label.setPixmap(make_pixmap(icon_path, size))
        return
    if icon_name:
        qi = QIcon.fromTheme(icon_name)
        if not qi.isNull():
            label.setPixmap(qi.pixmap(size, size))
            return
    if icon_name and icon_resolver:
        resolved = icon_resolver.resolve(icon_name)
        if resolved:
            label.setPixmap(make_pixmap(resolved, size))
            return

    label.setPixmap(_fallback(size, (item.get("name") or "?")[0].upper()))


def app_pixmap(item: dict, size: int, icon_resolver=None) -> QPixmap:
    """Return a QPixmap for an app item (no QLabel needed)."""
    icon_path = item.get("icon")
    icon_name = item.get("icon_name")

    if icon_path and os.path.exists(icon_path):
        return make_pixmap(icon_path, size)
    if icon_name:
        qi = QIcon.fromTheme(icon_name)
        if not qi.isNull():
            return qi.pixmap(size, size)
    if icon_name and icon_resolver:
        resolved = icon_resolver.resolve(icon_name)
        if resolved:
            return make_pixmap(resolved, size)

    return _fallback(size, (item.get("name") or "?")[0].upper())


def load_folder_icon(label, size: int) -> None:
    """Load a folder icon into a QLabel."""
    pix = folder_pixmap(size)
    label.setPixmap(pix)


def folder_pixmap(size: int) -> QPixmap:
    """Return a QPixmap for a folder."""
    installed = os.path.expanduser("~/.local/share/icons/linxpad-folder.png")
    bundled = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "icons", "linxpad-folder.png")
    )
    path = installed if os.path.exists(installed) else bundled
    if os.path.exists(path):
        return make_pixmap(path, size)
    qi = QIcon.fromTheme("folder")
    if not qi.isNull():
        return qi.pixmap(size, size)
    return _fallback(size, "📁")
