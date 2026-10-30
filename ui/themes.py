"""
Light and dark QSS theme stylesheets for the PDF Editor.

Provides a ThemeManager class that can apply polished light or dark themes
to the entire QApplication. The dark theme uses VS Code-like colours;
the light theme uses clean whites with a blue accent.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


class ThemeManager:
    """Manages light and dark themes for the application."""

    # ------------------------------------------------------------------ #
    #  Light theme – clean whites / light grays, accent #0078d4
    # ------------------------------------------------------------------ #
    LIGHT_THEME: str = """
    /* ---------- Global ---------- */
    * {
        font-family: "Segoe UI", "Noto Sans Bengali", "Noto Sans", sans-serif;
        font-size: 13px;
    }

    QMainWindow {
        background: #f5f5f5;
    }

    /* ---------- Menu bar ---------- */
    QMenuBar {
        background: #ffffff;
        border-bottom: 1px solid #e0e0e0;
        padding: 2px 0;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 10px;
        border-radius: 4px;
    }
    QMenuBar::item:selected {
        background: #e8e8e8;
    }
    QMenuBar::item:pressed {
        background: #d0d0d0;
    }

    /* ---------- Menus ---------- */
    QMenu {
        background: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 4px 0;
    }
    QMenu::item {
        padding: 6px 28px 6px 20px;
    }
    QMenu::item:selected {
        background: #0078d4;
        color: #ffffff;
        border-radius: 4px;
    }
    QMenu::separator {
        height: 1px;
        background: #e0e0e0;
        margin: 4px 8px;
    }
    QMenu::indicator {
        width: 16px;
        height: 16px;
        margin-left: 4px;
    }

    /* ---------- Toolbar ---------- */
    QToolBar {
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        spacing: 5px;
        padding: 5px 8px;
    }
    QToolBar::separator {
        width: 1px;
        background: #e2e8f0;
        margin: 5px 6px;
    }
    QToolButton {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
        color: #334155;
        min-width: 32px;
        min-height: 32px;
    }
    QToolButton:hover {
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
    }
    QToolButton:pressed {
        background: #e2e8f0;
    }
    QToolButton:checked {
        background: #e0f2fe;
        border: 1.5px solid #0284c7;
        color: #0284c7;
    }
    QToolButton:disabled {
        color: #94a3b8;
    }

    /* ---------- Dock widgets ---------- */
    QDockWidget {
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: bold;
        color: #333333;
    }
    QDockWidget::title {
        background: #f0f0f0;
        padding: 6px 8px;
        border-bottom: 1px solid #e0e0e0;
    }
    QDockWidget::close-button,
    QDockWidget::float-button {
        background: transparent;
        border: none;
        padding: 2px;
    }
    QDockWidget::close-button:hover,
    QDockWidget::float-button:hover {
        background: #e0e0e0;
        border-radius: 3px;
    }

    /* ---------- Properties Card Styling (Light) ---------- */
    QFrame#PropertiesCard {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
    QLabel#CardTitle {
        font-size: 13px;
        font-weight: 700;
        color: #0f172a;
        padding-bottom: 2px;
        border-bottom: 1px solid #f1f5f9;
    }
    QLabel#SectionLabel {
        font-size: 11px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        margin-top: 4px;
    }
    QPushButton#BoldToggleBtn, QPushButton#ItalicToggleBtn {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        color: #334155;
    }
    QPushButton#BoldToggleBtn:hover, QPushButton#ItalicToggleBtn:hover {
        background-color: #e2e8f0;
        border: 1px solid #94a3b8;
    }
    QPushButton#BoldToggleBtn:checked, QPushButton#ItalicToggleBtn:checked {
        background-color: #0284c7;
        border: 1.5px solid #0284c7;
        color: #ffffff;
    }
    QPushButton#SizeStepBtn {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        color: #1e293b;
        font-size: 15px;
        font-weight: 700;
        padding: 0px;
    }
    QPushButton#SizeStepBtn:hover {
        background-color: #e2e8f0;
        border: 1px solid #0284c7;
        color: #0284c7;
    }
    QPushButton#SizeStepBtn:pressed {
        background-color: #cbd5e1;
    }
    QPushButton#ColorPickerBtn {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 4px 10px;
        text-align: left;
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 12px;
        font-weight: 600;
        color: #334155;
    }
    QPushButton#ColorPickerBtn:hover {
        background-color: #f1f5f9;
        border: 1px solid #0284c7;
        color: #0284c7;
    }

    /* ---------- List widget (thumbnails etc.) ---------- */
    QListWidget {
        background: #fafafa;
        border: none;
        outline: none;
    }
    QListWidget::item {
        padding: 4px;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background: #cce4f7;
        border: 1px solid #0078d4;
    }
    QListWidget::item:hover:!selected {
        background: #e8e8e8;
    }

    /* ---------- Graphics view ---------- */
    QGraphicsView {
        background: #e0e0e0;
        border: none;
    }

    /* ---------- Labels ---------- */
    QLabel {
        color: #333333;
        background: transparent;
    }

    /* ---------- Combo box ---------- */
    QComboBox {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
        color: #333333;
    }
    QComboBox:hover {
        border: 1px solid #0078d4;
    }
    QComboBox:focus {
        border: 1px solid #0078d4;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #c0c0c0;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
    }
    QComboBox QAbstractItemView {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }

    /* ---------- Spin boxes ---------- */
    QSpinBox, QDoubleSpinBox {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 4px 6px;
        min-height: 22px;
        color: #333333;
    }
    QSpinBox:hover, QDoubleSpinBox:hover {
        border: 1px solid #0078d4;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #0078d4;
    }

    /* ---------- Push button ---------- */
    QPushButton {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 6px 16px;
        color: #333333;
        min-height: 22px;
    }
    QPushButton:hover {
        background: #e8e8e8;
        border: 1px solid #0078d4;
    }
    QPushButton:pressed {
        background: #d0d0d0;
    }
    QPushButton:disabled {
        background: #f0f0f0;
        color: #b0b0b0;
        border: 1px solid #d0d0d0;
    }
    QPushButton[primary="true"] {
        background: #0078d4;
        color: #ffffff;
        border: 1px solid #0078d4;
    }
    QPushButton[primary="true"]:hover {
        background: #106ebe;
    }
    QPushButton[primary="true"]:pressed {
        background: #005a9e;
    }

    /* ---------- Line edit ---------- */
    QLineEdit {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
        color: #333333;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QLineEdit:hover {
        border: 1px solid #0078d4;
    }
    QLineEdit:focus {
        border: 1px solid #0078d4;
    }

    /* ---------- Text edit ---------- */
    QTextEdit {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 4px;
        color: #333333;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QTextEdit:focus {
        border: 1px solid #0078d4;
    }

    /* ---------- Scroll bars ---------- */
    QScrollBar:vertical {
        background: #f5f5f5;
        width: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 30px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        border: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: transparent;
    }

    QScrollBar:horizontal {
        background: #f5f5f5;
        height: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        min-width: 30px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
        border: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: transparent;
    }

    /* ---------- Status bar ---------- */
    QStatusBar {
        background: #007acc;
        color: #ffffff;
        border-top: none;
        min-height: 24px;
    }
    QStatusBar::item {
        border: none;
    }
    QStatusBar QLabel {
        color: #ffffff;
        padding: 0 8px;
    }

    /* ---------- Splitter ---------- */
    QSplitter::handle {
        background: #e0e0e0;
        width: 2px;
        height: 2px;
    }
    QSplitter::handle:hover {
        background: #0078d4;
    }

    /* ---------- Tab widget ---------- */
    QTabWidget::pane {
        border: 1px solid #c0c0c0;
        background: #ffffff;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #f0f0f0;
        border: 1px solid #c0c0c0;
        padding: 6px 14px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        border-bottom-color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background: #e8e8e8;
    }

    /* ---------- Group box ---------- */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: #333333;
    }

    /* ---------- Check box ---------- */
    QCheckBox {
        spacing: 6px;
        color: #333333;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #c0c0c0;
        border-radius: 3px;
        background: #ffffff;
    }
    QCheckBox::indicator:checked {
        background: #0078d4;
        border-color: #0078d4;
    }
    QCheckBox::indicator:hover {
        border-color: #0078d4;
    }

    /* ---------- Slider ---------- */
    QSlider::groove:horizontal {
        height: 4px;
        background: #d0d0d0;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #0078d4;
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #106ebe;
    }
    QSlider::sub-page:horizontal {
        background: #0078d4;
        border-radius: 2px;
    }

    /* ---------- Dialog ---------- */
    QDialog {
        background: #f5f5f5;
    }

    /* ---------- Text browser ---------- */
    QTextBrowser {
        background: #ffffff;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        padding: 8px;
        color: #333333;
    }

    /* ---------- Frame ---------- */
    QFrame[frameShape="4"] {  /* HLine */
        color: #d0d0d0;
        max-height: 1px;
    }
    QFrame[frameShape="5"] {  /* VLine */
        color: #d0d0d0;
        max-width: 1px;
    }

    /* ---------- Message box ---------- */
    QMessageBox {
        background: #f5f5f5;
    }
    QMessageBox QLabel {
        color: #333333;
    }
    """

    # ------------------------------------------------------------------ #
    #  Dark theme – VS Code inspired (#1e1e1e bg, #252526 sidebar, #007acc accent)
    # ------------------------------------------------------------------ #
    DARK_THEME: str = """
    /* ---------- Global ---------- */
    * {
        font-family: "Segoe UI", "Noto Sans Bengali", "Noto Sans", sans-serif;
        font-size: 13px;
    }

    QMainWindow {
        background: #1e1e1e;
    }

    /* ---------- Menu bar ---------- */
    QMenuBar {
        background: #3c3c3c;
        border-bottom: 1px solid #333333;
        padding: 2px 0;
        color: #cccccc;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 10px;
        border-radius: 4px;
        color: #cccccc;
    }
    QMenuBar::item:selected {
        background: #505050;
    }
    QMenuBar::item:pressed {
        background: #007acc;
        color: #ffffff;
    }

    /* ---------- Menus ---------- */
    QMenu {
        background: #252526;
        border: 1px solid #454545;
        border-radius: 6px;
        padding: 4px 0;
        color: #cccccc;
    }
    QMenu::item {
        padding: 6px 28px 6px 20px;
    }
    QMenu::item:selected {
        background: #094771;
        color: #ffffff;
        border-radius: 4px;
    }
    QMenu::item:disabled {
        color: #6a6a6a;
    }
    QMenu::separator {
        height: 1px;
        background: #454545;
        margin: 4px 8px;
    }

    /* ---------- Toolbar ---------- */
    QToolBar {
        background: #1e1e24;
        border-bottom: 1px solid #2e2e38;
        spacing: 5px;
        padding: 5px 8px;
    }
    QToolBar::separator {
        width: 1px;
        background: #3f3f4e;
        margin: 5px 6px;
    }
    QToolButton {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
        color: #e2e8f0;
        min-width: 32px;
        min-height: 32px;
    }
    QToolButton:hover {
        background: #2e2e38;
        border: 1px solid #4a4a5a;
    }
    QToolButton:pressed {
        background: #3f3f4e;
    }
    QToolButton:checked {
        background: #0c4a6e;
        border: 1.5px solid #38bdf8;
        color: #ffffff;
    }
    QToolButton:disabled {
        color: #64748b;
    }

    /* ---------- Dock widgets ---------- */
    QDockWidget {
        font-weight: bold;
        color: #cccccc;
    }
    QDockWidget::title {
        background: #252526;
        padding: 6px 8px;
        border-bottom: 1px solid #333333;
    }
    QDockWidget::close-button,
    QDockWidget::float-button {
        background: transparent;
        border: none;
        padding: 2px;
    }
    QDockWidget::close-button:hover,
    QDockWidget::float-button:hover {
        background: #505050;
        border-radius: 3px;
    }

    /* ---------- Properties Card Styling (Dark) ---------- */
    QFrame#PropertiesCard {
        background-color: #25252b;
        border: 1px solid #33333e;
        border-radius: 8px;
    }
    QLabel#CardTitle {
        font-size: 13px;
        font-weight: 700;
        color: #f1f5f9;
        padding-bottom: 2px;
        border-bottom: 1px solid #2e2e38;
    }
    QLabel#SectionLabel {
        font-size: 11px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        margin-top: 4px;
    }
    QPushButton#BoldToggleBtn, QPushButton#ItalicToggleBtn {
        background-color: #1e1e24;
        border: 1px solid #3f3f4e;
        border-radius: 6px;
        color: #e2e8f0;
    }
    QPushButton#BoldToggleBtn:hover, QPushButton#ItalicToggleBtn:hover {
        background-color: #2e2e38;
        border: 1px solid #5a5a6e;
    }
    QPushButton#BoldToggleBtn:checked, QPushButton#ItalicToggleBtn:checked {
        background-color: #0284c7;
        border: 1.5px solid #38bdf8;
        color: #ffffff;
    }
    QPushButton#SizeStepBtn {
        background-color: #1e1e24;
        border: 1px solid #3f3f4e;
        border-radius: 6px;
        color: #e2e8f0;
        font-size: 15px;
        font-weight: 700;
        padding: 0px;
    }
    QPushButton#SizeStepBtn:hover {
        background-color: #2e2e38;
        border: 1px solid #38bdf8;
        color: #38bdf8;
    }
    QPushButton#SizeStepBtn:pressed {
        background-color: #3f3f4e;
    }
    QPushButton#ColorPickerBtn {
        background-color: #1e1e24;
        border: 1px solid #3f3f4e;
        border-radius: 6px;
        padding: 4px 10px;
        text-align: left;
        font-family: "Segoe UI", "Noto Sans", sans-serif;
        font-size: 12px;
        font-weight: 600;
        color: #e2e8f0;
    }
    QPushButton#ColorPickerBtn:hover {
        background-color: #2e2e38;
        border: 1px solid #38bdf8;
        color: #38bdf8;
    }

    /* ---------- List widget ---------- */
    QListWidget {
        background: #252526;
        border: none;
        outline: none;
        color: #cccccc;
    }
    QListWidget::item {
        padding: 4px;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background: #094771;
        border: 1px solid #007acc;
    }
    QListWidget::item:hover:!selected {
        background: #2a2d2e;
    }

    /* ---------- Graphics view ---------- */
    QGraphicsView {
        background: #1e1e1e;
        border: none;
    }

    /* ---------- Labels ---------- */
    QLabel {
        color: #cccccc;
        background: transparent;
    }

    /* ---------- Combo box ---------- */
    QComboBox {
        background: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
        color: #cccccc;
    }
    QComboBox:hover {
        border: 1px solid #007acc;
    }
    QComboBox:focus {
        border: 1px solid #007acc;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #555555;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
    }
    QComboBox QAbstractItemView {
        background: #252526;
        border: 1px solid #555555;
        selection-background-color: #094771;
        selection-color: #ffffff;
        color: #cccccc;
    }

    /* ---------- Spin boxes ---------- */
    QSpinBox, QDoubleSpinBox {
        background: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 6px;
        min-height: 22px;
        color: #cccccc;
    }
    QSpinBox:hover, QDoubleSpinBox:hover {
        border: 1px solid #007acc;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #007acc;
    }

    /* ---------- Push button ---------- */
    QPushButton {
        background: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 6px 16px;
        color: #cccccc;
        min-height: 22px;
    }
    QPushButton:hover {
        background: #505050;
        border: 1px solid #007acc;
    }
    QPushButton:pressed {
        background: #606060;
    }
    QPushButton:disabled {
        background: #2d2d2d;
        color: #6a6a6a;
        border: 1px solid #3c3c3c;
    }
    QPushButton[primary="true"] {
        background: #007acc;
        color: #ffffff;
        border: 1px solid #007acc;
    }
    QPushButton[primary="true"]:hover {
        background: #1c97ea;
    }
    QPushButton[primary="true"]:pressed {
        background: #005a9e;
    }

    /* ---------- Line edit ---------- */
    QLineEdit {
        background: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
        color: #cccccc;
        selection-background-color: #264f78;
        selection-color: #ffffff;
    }
    QLineEdit:hover {
        border: 1px solid #007acc;
    }
    QLineEdit:focus {
        border: 1px solid #007acc;
    }

    /* ---------- Text edit ---------- */
    QTextEdit {
        background: #1e1e1e;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px;
        color: #cccccc;
        selection-background-color: #264f78;
        selection-color: #ffffff;
    }
    QTextEdit:focus {
        border: 1px solid #007acc;
    }

    /* ---------- Scroll bars ---------- */
    QScrollBar:vertical {
        background: #1e1e1e;
        width: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #5a5a5a;
        min-height: 30px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: #787878;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        border: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: transparent;
    }

    QScrollBar:horizontal {
        background: #1e1e1e;
        height: 12px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #5a5a5a;
        min-width: 30px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #787878;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
        border: none;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: transparent;
    }

    /* ---------- Status bar ---------- */
    QStatusBar {
        background: #007acc;
        color: #ffffff;
        border-top: none;
        min-height: 24px;
    }
    QStatusBar::item {
        border: none;
    }
    QStatusBar QLabel {
        color: #ffffff;
        padding: 0 8px;
    }

    /* ---------- Splitter ---------- */
    QSplitter::handle {
        background: #333333;
        width: 2px;
        height: 2px;
    }
    QSplitter::handle:hover {
        background: #007acc;
    }

    /* ---------- Tab widget ---------- */
    QTabWidget::pane {
        border: 1px solid #454545;
        background: #1e1e1e;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #2d2d2d;
        border: 1px solid #454545;
        padding: 6px 14px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        color: #969696;
    }
    QTabBar::tab:selected {
        background: #1e1e1e;
        border-bottom-color: #1e1e1e;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background: #383838;
    }

    /* ---------- Group box ---------- */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #454545;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 16px;
        color: #cccccc;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: #cccccc;
    }

    /* ---------- Check box ---------- */
    QCheckBox {
        spacing: 6px;
        color: #cccccc;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #555555;
        border-radius: 3px;
        background: #3c3c3c;
    }
    QCheckBox::indicator:checked {
        background: #007acc;
        border-color: #007acc;
    }
    QCheckBox::indicator:hover {
        border-color: #007acc;
    }

    /* ---------- Slider ---------- */
    QSlider::groove:horizontal {
        height: 4px;
        background: #555555;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #007acc;
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background: #1c97ea;
    }
    QSlider::sub-page:horizontal {
        background: #007acc;
        border-radius: 2px;
    }

    /* ---------- Dialog ---------- */
    QDialog {
        background: #252526;
        color: #cccccc;
    }

    /* ---------- Text browser ---------- */
    QTextBrowser {
        background: #1e1e1e;
        border: 1px solid #454545;
        border-radius: 4px;
        padding: 8px;
        color: #cccccc;
    }

    /* ---------- Frame ---------- */
    QFrame[frameShape="4"] {
        color: #454545;
        max-height: 1px;
    }
    QFrame[frameShape="5"] {
        color: #454545;
        max-width: 1px;
    }

    /* ---------- Message box ---------- */
    QMessageBox {
        background: #252526;
    }
    QMessageBox QLabel {
        color: #cccccc;
    }
    """

    @staticmethod
    def apply_theme(app: QApplication, dark: bool = False) -> None:
        """Apply the specified theme to the application.

        Args:
            app: The QApplication instance.
            dark: If True apply the dark theme, otherwise apply the light theme.
        """
        if app is None:
            return
        stylesheet = ThemeManager.DARK_THEME if dark else ThemeManager.LIGHT_THEME
        app.setStyleSheet(stylesheet)

    @staticmethod
    def get_icon_color(dark: bool = False) -> str:
        """Return the appropriate icon/text colour for the current theme.

        Args:
            dark: Whether the dark theme is active.

        Returns:
            A hex colour string suitable for icons or text drawn on the theme
            background.
        """
        return "#cccccc" if dark else "#333333"
