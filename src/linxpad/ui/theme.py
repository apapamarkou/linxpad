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

# All stylesheets and colour constants for LinxPad UI.
from PyQt6.QtGui import QColor

# ── Window ────────────────────────────────────────────────────────────────────
MAIN_STYLESHEET = """
QMainWindow { background-color: #1e1e1e; }
QLineEdit {
    background-color: #2d2d2d; color: #ffffff;
    border: 2px solid #404040; border-radius: 8px;
    padding: 12px; font-size: 18px;
}
QScrollArea { background-color: transparent; border: none; }
"""

# ── Grid ──────────────────────────────────────────────────────────────────────
GRID_BG = "#1e1e1e"
FOLDER_BG = "#181818"

# ── Icon item colours ─────────────────────────────────────────────────────────
C_NORMAL_HOVER = QColor(255, 255, 255, 38)
C_FOLDER_BG = QColor(100, 100, 100, 38)
C_FOLDER_HOVER = QColor(200, 200, 200, 71)
C_FOLDER_BORDER = QColor(255, 255, 255, 64)
C_SELECTED_BG = QColor(128, 128, 128, 153)
C_SELECTED_HOVER = QColor(128, 128, 128, 191)
C_SELECTED_BORDER = QColor(170, 170, 170, 255)
C_DROP_TARGET_BG = QColor(255, 255, 255, 30)
C_DROP_TARGET_BORDER = QColor(255, 255, 255, 180)
C_GHOST_BG = QColor(255, 255, 255, 18)

# ── Labels ────────────────────────────────────────────────────────────────────
LABEL_IDLE = (
    "color: #ffffff; font-size: 20px; font-weight: bold;"
    "background-color: rgba(20,20,20,0.92);"
    "border: 2px solid #888888; border-radius: 12px; padding: 14px 32px;"
)
LABEL_HOT = (
    "color: #ffffff; font-size: 20px; font-weight: bold;"
    "background-color: rgba(20,20,20,0.92);"
    "border: 2px solid #ff5050; border-radius: 12px; padding: 14px 32px;"
)
TITLE_LABEL = "color: white; font-size: 24px; font-weight: bold; background: transparent;"
TITLE_EDIT = (
    "color: white; font-size: 24px; font-weight: bold;"
    "background-color: #2d2d2d; border: 2px solid #606060;"
    "border-radius: 6px; padding: 2px 8px;"
)

# ── Search rows ───────────────────────────────────────────────────────────────
ROW_NORMAL = (
    "QWidget { background: transparent; border-radius: 8px; }"
    "QWidget:hover { background-color: rgba(255,255,255,0.08); }"
)
ROW_SELECTED = (
    "QWidget { background-color: rgba(126,184,247,40);"
    " border-bottom: 1px solid rgba(126,184,247,80); border-radius: 0px; }"
)
ROW_NAME = "color: #ffffff; font-size: 16px; font-weight: bold; background: transparent;"
ROW_SUB = "color: #aaaaaa; font-size: 13px; background: transparent;"
ROW_PATH = "color: #888888; font-size: 16px; background: transparent;"
ROW_URL = "color: #888888; font-size: 13px; background: transparent;"
ROW_LINK = "color: #7eb8f7; font-size: 16px; font-weight: bold; background: transparent;"
ROW_DESC = "color: #666666; font-size: 12px; background: transparent;"
SECTION_HEADER = (
    "color: #aaaaaa; font-size: 20px; font-weight: bold;"
    "letter-spacing: 1px; background: transparent;"
)

# ── Page dots ─────────────────────────────────────────────────────────────────
DOT_ACTIVE = "background-color: #ffffff; border-radius: 5px; margin: 9px;"
DOT_INACTIVE = "background-color: rgba(255,255,255,0.35); border-radius: 5px; margin: 9px;"

# ── Flip zones ────────────────────────────────────────────────────────────────
FLIP_ZONE_IDLE = (
    "color: rgba(255,255,255,0.0); font-size: 32px;" "background-color: rgba(255,255,255,0.0);"
)
FLIP_ZONE_HOT = (
    "color: rgba(255,255,255,0.7); font-size: 32px;"
    "background-color: rgba(255,255,255,0.08);"
    "border-radius: 12px;"
)

# ── Scroll areas ──────────────────────────────────────────────────────────────
SCROLL_FOLDER = (
    "QScrollArea { background-color: #1a1a1a; border: 1px solid #555; border-radius: 12px; }"
)
SCROLL_MAIN = "QScrollArea { background-color: #1e1e1e; border: none; }"
