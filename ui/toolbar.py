"""
Main toolbar for the PDF Editor.

Provides an :class:`EditorToolBar` with tool buttons for file operations,
undo/redo, drawing/annotation tools, zoom controls, and a Bangla input toggle.
Uses professional SVG vector icons.
"""

from __future__ import annotations

import os
import sys
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QLabel, QToolBar, QToolButton, QWidget

if TYPE_CHECKING:
    from ui.i18n import I18n

ICON_DIR = Path(__file__).parent.parent / "icons"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ICON_DIR = Path(sys._MEIPASS) / "icons"


def get_icon(filename: str) -> QIcon:
    """Load an icon from the icons directory."""
    path = ICON_DIR / filename
    if path.exists():
        return QIcon(str(path))
    return QIcon()


def get_toggle_icon(base_name: str) -> QIcon:
    """Load an icon with off and on (checked) state variants."""
    icon = QIcon()
    off_path = ICON_DIR / f"{base_name}.svg"
    on_path = ICON_DIR / f"{base_name}-white.svg"
    if off_path.exists():
        icon.addFile(str(off_path), state=QIcon.State.Off)
    if on_path.exists():
        icon.addFile(str(on_path), state=QIcon.State.On)
    elif off_path.exists():
        icon.addFile(str(off_path), state=QIcon.State.On)
    return icon


class Tool(Enum):
    """Available editing tools."""

    SELECT = auto()
    TEXT = auto()
    HIGHLIGHT = auto()
    UNDERLINE = auto()
    STRIKETHROUGH = auto()
    RECTANGLE = auto()
    LINE = auto()
    ARROW = auto()
    FREEHAND = auto()
    IMAGE = auto()
    SIGNATURE = auto()
    ERASER = auto()


# Mapping from Tool enum to (svg_filename, fallback_label, tooltip_i18n_key)
_TOOL_DEFS: list[tuple[Tool, str, str, str]] = [
    (Tool.SELECT, "select.svg", "Select", "tool_select"),
    (Tool.TEXT, "text.svg", "Text", "tool_text"),
    (Tool.HIGHLIGHT, "highlight.svg", "Highlight", "tool_highlight"),
    (Tool.UNDERLINE, "underline.svg", "Underline", "tool_underline"),
    (Tool.STRIKETHROUGH, "strikethrough.svg", "Strike", "tool_strikethrough"),
    (Tool.RECTANGLE, "rectangle.svg", "Rect", "tool_rectangle"),
    (Tool.LINE, "line.svg", "Line", "tool_line"),
    (Tool.ARROW, "arrow.svg", "Arrow", "tool_arrow"),
    (Tool.FREEHAND, "pen.svg", "Pen", "tool_pen"),
    (Tool.IMAGE, "image.svg", "Image", "tool_image"),
    (Tool.SIGNATURE, "signature.svg", "Sign", "tool_signature"),
    (Tool.ERASER, "eraser.svg", "Eraser", "tool_eraser"),
]


class EditorToolBar(QToolBar):
    """Main toolbar for the PDF editor."""

    # ---- Signals ---- #
    tool_selected = Signal(Tool)
    open_requested = Signal()
    save_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    bangla_toggled = Signal(bool)
    delete_requested = Signal()

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setObjectName("EditorToolBar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(22, 22))

        # ---- File operations ---- #
        self._open_action = self._make_action("open.svg", "📂", "open_file", self.open_requested.emit)
        self._save_action = self._make_action("save.svg", "💾", "save_file", self.save_requested.emit)

        self.addSeparator()

        # ---- Undo / Redo / Delete ---- #
        self._undo_action = self._make_action("undo.svg", "↩", "undo", self.undo_requested.emit)
        self._redo_action = self._make_action("redo.svg", "↪", "redo", self.redo_requested.emit)
        self._undo_action.setEnabled(False)
        self._redo_action.setEnabled(False)

        self._delete_action = self._make_action("delete.svg", "🗑", "action_delete", self.delete_requested.emit)

        self.addSeparator()

        # ---- Drawing / annotation tools (exclusive checkable group) ---- #
        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)
        self._tool_actions: dict[Tool, QAction] = {}

        for tool, svg_name, fallback_text, key in _TOOL_DEFS:
            action = QAction(self)
            icon = get_icon(svg_name)
            if not icon.isNull():
                action.setIcon(icon)
            else:
                action.setText(fallback_text)
            action.setCheckable(True)
            action.setToolTip(self._i18n.t(key))
            action.setData(tool)
            action.triggered.connect(self._on_tool_action)
            self._tool_group.addAction(action)
            self.addAction(action)
            self._tool_actions[tool] = action

        # Default: SELECT is checked
        self._tool_actions[Tool.SELECT].setChecked(True)

        self.addSeparator()

        # ---- Zoom ---- #
        self._zoom_in_action = self._make_action("zoom-in.svg", "🔍+", "zoom_in", self.zoom_in_requested.emit)
        self._zoom_out_action = self._make_action("zoom-out.svg", "🔍-", "zoom_out", self.zoom_out_requested.emit)

        self.addSeparator()

        # ---- Bangla input toggle ---- #
        self._bangla_action = QAction(self)
        b_icon = get_icon("bangla.svg")
        if not b_icon.isNull():
            self._bangla_action.setIcon(b_icon)
        else:
            self._bangla_action.setText("বাং")
        self._bangla_action.setCheckable(True)
        self._bangla_action.setToolTip(self._i18n.t("toggle_bangla"))
        self._bangla_action.toggled.connect(self.bangla_toggled.emit)
        self.addAction(self._bangla_action)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _make_action(self, svg_name: str, fallback_label: str, i18n_key: str, slot: object) -> QAction:
        """Create a non-checkable QAction with SVG icon and connect it."""
        action = QAction(self)
        icon = get_icon(svg_name)
        if not icon.isNull():
            action.setIcon(icon)
        else:
            action.setText(fallback_label)
        action.setToolTip(self._i18n.t(i18n_key))
        action.triggered.connect(slot)  # type: ignore[arg-type]
        self.addAction(action)
        return action

    def _on_tool_action(self) -> None:
        action = self._tool_group.checkedAction()
        if action is not None:
            tool: Tool = action.data()
            self.tool_selected.emit(tool)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    @property
    def current_tool(self) -> Tool:
        action = self._tool_group.checkedAction()
        if action is not None:
            return action.data()
        return Tool.SELECT

    def update_undo_redo(self, can_undo: bool, can_redo: bool) -> None:
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)

    def set_current_tool(self, tool: Tool) -> None:
        action = self._tool_actions.get(tool)
        if action is not None:
            action.setChecked(True)

    def update_translations(self, i18n: I18n) -> None:
        self._i18n = i18n
        self._open_action.setToolTip(i18n.t("open_file"))
        self._save_action.setToolTip(i18n.t("save_file"))
        self._undo_action.setToolTip(i18n.t("undo"))
        self._redo_action.setToolTip(i18n.t("redo"))
        self._delete_action.setToolTip(i18n.t("action_delete"))
        self._zoom_in_action.setToolTip(i18n.t("zoom_in"))
        self._zoom_out_action.setToolTip(i18n.t("zoom_out"))
        self._bangla_action.setToolTip(i18n.t("toggle_bangla"))

        for tool, _svg, _fallback, key in _TOOL_DEFS:
            action = self._tool_actions.get(tool)
            if action is not None:
                action.setToolTip(i18n.t(key))

    def set_bangla_active(self, active: bool) -> None:
        self._bangla_action.blockSignals(True)
        self._bangla_action.setChecked(active)
        self._bangla_action.blockSignals(False)
