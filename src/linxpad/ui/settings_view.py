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
 
"""Settings overlay panel for Full Screen Launcher."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

_SPACING_STEPS = [10, 20, 30, 40, 50, 60]

_PANEL_STYLE = """
QWidget#settings_panel {
    background-color: rgba(20, 20, 20, 0.97);
    border: 1px solid #444;
    border-radius: 16px;
}
QLabel {
    color: #cccccc;
    font-size: 14px;
    background: transparent;
}
QLabel#section {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    background: transparent;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #444;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #7eb8f7;
    border-radius: 2px;
}
QCheckBox {
    color: #cccccc;
    font-size: 14px;
    background: transparent;
    spacing: 10px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #666;
    border-radius: 4px;
    background: #2d2d2d;
}
QCheckBox::indicator:checked {
    background: #7eb8f7;
    border-color: #7eb8f7;
}
QTextBrowser {
    background-color: #2a2a2a;
    color: #aaaaaa;
    border: 1px solid #444;
    border-radius: 8px;
    font-size: 12px;
    padding: 8px;
}
"""

_ABOUT_HTML = """
<p style="color:#ffffff; font-size:15px; font-weight:bold; margin-bottom:4px;">
  LinxPad
</p>
<p style="color:#888888; font-size:12px; margin-top:0;">
  A macOS-style fullscreen launcher for Linux (X11 &amp; Wayland)
</p>
<p style="color:#666666; font-size:11px;">
  Built with Python &amp; PyQt6<br>
  GPL-3.0-or-later<br>
  <a href="https://github.com/apapamarkou/linxpad" style="color:#7eb8f7;">
    github.com/apapamarkou/linxpad
  </a>
</p>
"""


class SettingsView(QWidget):
    """Full-screen overlay with a centred settings panel.

    Signals:
        closed(cols, rows, spacing, transparency, keep_previous_state)
    """

    closed = pyqtSignal(int, int, int, int, bool)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_PANEL_STYLE)

        # ── dim background ────────────────────────────────────────────────────
        bg = QWidget(self)
        bg.setObjectName("dim")
        bg.setStyleSheet("background: rgba(0,0,0,0.6);")
        bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._bg = bg

        # ── panel ─────────────────────────────────────────────────────────────
        panel = QWidget(self)
        panel.setObjectName("settings_panel")
        panel.setFixedWidth(480)
        self._panel = panel

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        # Title
        title = QLabel("⚙  Settings")
        title.setObjectName("section")
        title.setStyleSheet(
            "color: white; font-size: 20px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        # Columns
        self._cols_slider, cols_row = self._make_slider("Columns", 5, 12, settings.cols)
        layout.addLayout(cols_row)

        # Rows
        self._rows_slider, rows_row = self._make_slider("Rows", 2, 6, settings.rows)
        layout.addLayout(rows_row)

        # Spacing (5 steps → indices 0-4 mapping to _SPACING_STEPS)
        sp_idx = self._spacing_to_idx(settings.spacing)
        self._spacing_slider, spacing_row = self._make_slider(
            "Icon spacing", 0, len(_SPACING_STEPS) - 1, sp_idx
        )
        self._spacing_val_label = spacing_row.itemAt(2).widget()
        self._spacing_slider.valueChanged.connect(self._update_spacing_label)
        layout.addLayout(spacing_row)
        self._update_spacing_label(sp_idx)

        # Transparency
        transp = max(50, min(90, int(settings.opacity * 100)))
        self._transp_slider, transp_row = self._make_slider("Transparency %", 50, 100, transp)
        layout.addLayout(transp_row)

        # Keep previous state
        self._keep_cb = QCheckBox("Keep search / folder state when re-opening")
        self._keep_cb.setChecked(settings.keep_previous_state)
        layout.addWidget(self._keep_cb)

        # About
        about_label = QLabel("About")
        about_label.setObjectName("section")
        about_label.setStyleSheet(
            "color: #888; font-size: 13px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(about_label)

        about = QTextBrowser()
        about.setFixedHeight(200)
        about.setOpenExternalLinks(True)
        about.setHtml(_ABOUT_HTML)
        layout.addWidget(about)

        hint = QLabel("Press Enter or Esc to close and apply")
        hint.setStyleSheet("color: #555; font-size: 11px; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── layout ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._bg.setGeometry(self.rect())
        pw = self._panel.width()
        ph = self._panel.sizeHint().height()
        self._panel.setGeometry(
            (self.width() - pw) // 2,
            (self.height() - ph) // 2,
            pw,
            ph,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _make_slider(self, label: str, lo: int, hi: int, val: int):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(f"{label}:")
        lbl.setFixedWidth(140)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(val)
        val_lbl = QLabel(str(val))
        val_lbl.setFixedWidth(32)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda v, w=val_lbl: w.setText(str(v)))
        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(val_lbl)
        return slider, row

    def _spacing_to_idx(self, spacing: int) -> int:
        closest = min(range(len(_SPACING_STEPS)), key=lambda i: abs(_SPACING_STEPS[i] - spacing))
        return closest

    def _update_spacing_label(self, idx: int) -> None:
        self._spacing_val_label.setText(str(_SPACING_STEPS[idx]))

    # ── close / apply ─────────────────────────────────────────────────────────

    def _apply_and_close(self) -> None:
        cols = self._cols_slider.value()
        rows = self._rows_slider.value()
        spacing = _SPACING_STEPS[self._spacing_slider.value()]
        transp = self._transp_slider.value()
        keep = self._keep_cb.isChecked()
        self.closed.emit(cols, rows, spacing, transp, keep)
        self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._apply_and_close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        # Click outside the panel → close
        if not self._panel.geometry().contains(event.pos()):
            self._apply_and_close()
        else:
            super().mousePressEvent(event)
