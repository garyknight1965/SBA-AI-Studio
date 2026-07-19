"""
============================================================
SBA AI Studio
Theme
GUI-011
Version : 1.0.0
============================================================

A real dark theme for the app, replacing the plain, unstyled
default Qt look. Previously "theme": "dark" existed in
config/settings.json but was read nowhere in the codebase - this
module is what actually makes that setting do something.

apply_theme(theme_name) is safe to call multiple times (e.g. from
the Settings dialog, so a theme change is visible immediately
without restarting the app) - it always replaces the whole
stylesheet on the running QApplication instance rather than
appending to it.

"light" applies an empty stylesheet, restoring Qt's native
default look exactly - never a half-styled hybrid.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

# A clean, moderately dark palette - not pure black (harsh under
# long editing sessions), consistent contrast for text at every
# level (primary body text vs. secondary/muted labels).
_BG = "#1e1f22"
_PANEL_BG = "#26272b"
_PANEL_BG_ALT = "#2c2d31"
_BORDER = "#3a3b3f"
_TEXT = "#e4e4e6"
_TEXT_MUTED = "#9aa0a6"
_ACCENT = "#4f8cff"
_ACCENT_HOVER = "#6ea0ff"
_ACCENT_PRESSED = "#3b6fd6"
_DISABLED_BG = "#2a2b2e"
_DISABLED_TEXT = "#6b6d70"

DARK_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-size: 13px;
}}

QDockWidget {{
    color: {_TEXT};
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}

QDockWidget::title {{
    background-color: {_PANEL_BG_ALT};
    padding: 6px 8px;
    border: 1px solid {_BORDER};
    border-bottom: none;
    font-weight: 600;
}}

QDockWidget > QWidget {{
    background-color: {_PANEL_BG};
    border: 1px solid {_BORDER};
    border-top: none;
}}

QGroupBox {{
    background-color: {_PANEL_BG};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {_TEXT_MUTED};
}}

QLabel {{
    background: transparent;
    color: {_TEXT};
}}

QMenuBar {{
    background-color: {_PANEL_BG_ALT};
    color: {_TEXT};
    border-bottom: 1px solid {_BORDER};
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 12px;
}}

QMenuBar::item:selected {{
    background-color: {_ACCENT};
    color: white;
    border-radius: 4px;
}}

QMenu {{
    background-color: {_PANEL_BG_ALT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
}}

QMenu::item:selected {{
    background-color: {_ACCENT};
    color: white;
}}

QStatusBar {{
    background-color: {_PANEL_BG_ALT};
    color: {_TEXT_MUTED};
    border-top: 1px solid {_BORDER};
}}

QToolBar {{
    background-color: {_PANEL_BG_ALT};
    border: none;
    spacing: 4px;
}}

QPushButton {{
    background-color: {_PANEL_BG_ALT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 5px;
    padding: 7px 14px;
}}

QPushButton:hover {{
    border-color: {_ACCENT};
}}

QPushButton:pressed {{
    background-color: {_ACCENT_PRESSED};
    color: white;
}}

QPushButton:disabled {{
    background-color: {_DISABLED_BG};
    color: {_DISABLED_TEXT};
    border-color: {_BORDER};
}}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
QComboBox {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {_ACCENT};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {_ACCENT};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {_DISABLED_BG};
    color: {_DISABLED_TEXT};
}}

QCheckBox {{
    color: {_TEXT};
    spacing: 8px;
}}

QListWidget, QTreeWidget, QTableWidget {{
    background-color: {_BG};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    alternate-background-color: {_PANEL_BG_ALT};
}}

QHeaderView::section {{
    background-color: {_PANEL_BG_ALT};
    color: {_TEXT_MUTED};
    padding: 4px 6px;
    border: 1px solid {_BORDER};
}}

QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: {_BG};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {_BORDER};
    min-height: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {_ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {_BG};
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {_BORDER};
    min-width: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {_ACCENT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""


def apply_theme(theme_name: str) -> None:
    """
    Applies "dark" or "light" to the currently running
    QApplication instance. "light" clears the stylesheet
    entirely, restoring Qt's native default look. Any other
    value falls back to "light" - an unrecognised theme name
    should never leave the app in a broken half-styled state.

    Safe to call repeatedly (e.g. from the Settings dialog on
    OK) - always replaces the whole stylesheet, never appends.
    """

    app = QApplication.instance()

    if app is None:
        return

    if theme_name == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet("")