"""
Main Application Window for the PDF Editor.

Coordinates the PDF rendering engine, editor canvas, sidebars, toolbar,
menus, undo/redo system, Avro-style Bangla phonetic input, and i18n.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
)

from core.annotations import (
    AddFreehandCommand,
    AddHighlightCommand,
    AddImageCommand,
    AddShapeCommand,
    AddTextBoxCommand,
    ModifyTextBoxCommand,
    RedactCommand,
    RemoveFreehandCommand,
    RemoveHighlightCommand,
    RemoveImageCommand,
    RemoveShapeCommand,
    RemoveTextBoxCommand,
)
from core.bangla_input import BanglaPhoneticEngine
from core.page_tools import (
    DeletePageCommand,
    InsertBlankPageCommand,
    PageTools,
    ReorderPagesCommand,
    RotatePageCommand,
)
from core.pdf_engine import PdfEngine
from core.undo_redo import UndoStack
from ui.dialogs import AboutDialog, ExportImageDialog, MergeDialog, SplitDialog
from ui.i18n import I18n, Language
from ui.pdf_view import PdfView
from ui.properties_panel import PropertiesPanel
from ui.themes import ThemeManager
from ui.thumbnail_panel import ThumbnailPanel
from ui.toolbar import EditorToolBar, Tool
from ui.welcome_screen import RecentFilesManager, WelcomeScreen

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for RuhiPdf Editor."""

    def __init__(self) -> None:
        super().__init__()

        # Set Application Icon
        app_icon_path = Path(__file__).parent.parent / "icons" / "app_icon.png"
        if app_icon_path.exists():
            self.setWindowIcon(QIcon(str(app_icon_path)))

        # 1. Core Model & Engines
        self._engine = PdfEngine()
        self._undo_stack = UndoStack()
        self._bangla_engine = BanglaPhoneticEngine(self)
        self._i18n = I18n(Language.ENGLISH)
        self._is_dark_theme = False
        self._is_modified = False

        # 2. Setup Central Stack: Welcome Screen & PDF View
        self._stack = QStackedWidget(self)
        self._welcome = WelcomeScreen(self._i18n, self)
        self._welcome.file_selected.connect(self.open_file)
        self._stack.addWidget(self._welcome)

        self._view = PdfView(self)
        self._view.set_dependencies(self._engine, self._bangla_engine, self._i18n)
        self._stack.addWidget(self._view)

        self.setCentralWidget(self._stack)

        # 3. Setup Sidebars & Toolbar
        self._toolbar = EditorToolBar(self._i18n, self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        self._thumb_panel = ThumbnailPanel(self._i18n, self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._thumb_panel)

        self._prop_panel = PropertiesPanel(self._i18n, self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._prop_panel)

        # Populate available font families
        available_fonts = self._engine.text_renderer.get_font_families()
        self._prop_panel.set_font_families(available_fonts)

        # 4. Status Bar
        self._setup_status_bar()

        # 5. Menus & Actions
        self._setup_menus()

        # 6. Signals and Connections
        self._connect_signals()

        # 7. Install Bangla event filter on application for interactive input
        qapp = QApplication.instance()
        if qapp:
            qapp.installEventFilter(self._bangla_engine)

        # Apply Light Theme by default
        ThemeManager.apply_theme(QApplication.instance(), dark=False)
        self.retranslate_ui()

        # 8. Start with professional Welcome Screen
        self._show_welcome_screen()

        self.resize(1360, 850)
        logger.info("RuhiPdf Editor MainWindow initialized successfully.")

    # ================================================================== #
    #  Status Bar Setup
    # ================================================================== #

    def _setup_status_bar(self) -> None:
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        self._status_page_label = QLabel("Page: 1 / 1")
        self._status_zoom_label = QLabel("Zoom: 100%")
        self._status_bangla_label = QLabel("Bangla: OFF")
        self._status_bangla_label.setStyleSheet("font-weight: bold; padding: 0 8px;")

        self._status_bar.addPermanentWidget(self._status_page_label)
        self._status_bar.addPermanentWidget(self._status_zoom_label)
        self._status_bar.addPermanentWidget(self._status_bangla_label)
        self._status_bar.showMessage(self._i18n.t("ready"), 3000)

    # ================================================================== #
    #  Menu Setup
    # ================================================================== #

    def _setup_menus(self) -> None:
        mb = self.menuBar()

        # --- File Menu ---
        self._menu_file = mb.addMenu(self._i18n.t("menu_file"))

        self._act_open = self._menu_file.addAction(self._i18n.t("open_file"), self.action_open, QKeySequence.StandardKey.Open)
        self._act_save = self._menu_file.addAction(self._i18n.t("save_file"), self.action_save, QKeySequence.StandardKey.Save)
        self._act_save_as = self._menu_file.addAction(self._i18n.t("save_as"), self.action_save_as, QKeySequence.StandardKey.SaveAs)
        self._act_close = self._menu_file.addAction(self._i18n.t("close_file"), self.action_close_document, QKeySequence("Ctrl+W"))
        self._menu_file.addSeparator()
        self._act_export = self._menu_file.addAction(self._i18n.t("export_as_image"), self.action_export_image)
        self._menu_file.addSeparator()
        self._act_exit = self._menu_file.addAction(self._i18n.t("exit"), self.close, QKeySequence.StandardKey.Quit)

        # --- Edit Menu ---
        self._menu_edit = mb.addMenu(self._i18n.t("menu_edit"))
        self._act_undo = self._menu_edit.addAction(self._i18n.t("undo"), self.action_undo, QKeySequence.StandardKey.Undo)
        self._act_undo.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.addAction(self._act_undo)

        self._act_redo = self._menu_edit.addAction(self._i18n.t("redo"), self.action_redo, QKeySequence.StandardKey.Redo)
        self._act_redo.setShortcuts([QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Y")])
        self._act_redo.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.addAction(self._act_redo)

        self._act_del = self._menu_edit.addAction(self._i18n.t("action_delete"), self._view.delete_selected, QKeySequence.StandardKey.Delete)
        self._act_del.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.addAction(self._act_del)

        # --- View Menu ---
        self._menu_view = mb.addMenu(self._i18n.t("menu_view"))
        self._act_actual_size = self._menu_view.addAction(self._i18n.t("zoom_actual_size"), self._view.zoom_actual_size, QKeySequence("Ctrl+1"))
        self._act_zoom_fit = self._menu_view.addAction(self._i18n.t("zoom_fit_width"), self._view.zoom_fit_width, QKeySequence("Ctrl+0"))
        self._act_zoom_page = self._menu_view.addAction(self._i18n.t("zoom_fit_page"), self._view.zoom_fit_page, QKeySequence("Ctrl+2"))
        self._act_zoom_height = self._menu_view.addAction(self._i18n.t("zoom_fit_height"), self._view.zoom_fit_height, QKeySequence("Ctrl+3"))
        self._menu_view.addSeparator()
        self._act_zoom_in = self._menu_view.addAction(self._i18n.t("zoom_in"), self._view.zoom_in, QKeySequence.StandardKey.ZoomIn)
        self._act_zoom_out = self._menu_view.addAction(self._i18n.t("zoom_out"), self._view.zoom_out, QKeySequence.StandardKey.ZoomOut)
        self._menu_view.addSeparator()
        self._act_read_mode = self._menu_view.addAction(self._i18n.t("read_mode"), self.toggle_read_mode, QKeySequence("Ctrl+H"))
        self._act_full_screen = self._menu_view.addAction(self._i18n.t("full_screen"), self.toggle_full_screen, QKeySequence("F11"))
        self._menu_view.addSeparator()
        self._act_theme_toggle = self._menu_view.addAction(self._i18n.t("theme_dark"), self.toggle_theme)

        # --- Pages Menu ---
        self._menu_pages = mb.addMenu(self._i18n.t("menu_pages"))
        self._act_delete_page = self._menu_pages.addAction(self._i18n.t("delete_page"), self.action_delete_page)
        self._act_rotate_page = self._menu_pages.addAction(self._i18n.t("rotate_page"), self.action_rotate_page)
        self._act_insert_blank = self._menu_pages.addAction(self._i18n.t("insert_blank_page"), self.action_insert_blank_page)
        self._menu_pages.addSeparator()
        self._act_merge = self._menu_pages.addAction(self._i18n.t("merge_pdfs"), self.action_merge_pdfs)
        self._act_split = self._menu_pages.addAction(self._i18n.t("split_pdf"), self.action_split_pdf)

        # --- Language Menu ---
        self._menu_lang = mb.addMenu(self._i18n.t("menu_language"))
        self._act_lang_en = self._menu_lang.addAction(self._i18n.t("lang_english"), lambda: self.set_language(Language.ENGLISH))
        self._act_lang_bn = self._menu_lang.addAction(self._i18n.t("lang_bangla"), lambda: self.set_language(Language.BANGLA))

        # --- Help Menu ---
        self._menu_help = mb.addMenu(self._i18n.t("menu_help"))
        self._act_about = self._menu_help.addAction(self._i18n.t("about"), self.action_about)

    # ================================================================== #
    #  Signals & Connections
    # ================================================================== #

    def _connect_signals(self) -> None:
        # Toolbar actions
        self._toolbar.open_requested.connect(self.action_open)
        self._toolbar.save_requested.connect(self.action_save)
        self._toolbar.close_requested.connect(self.action_close_document)
        self._toolbar.undo_requested.connect(self.action_undo)
        self._toolbar.redo_requested.connect(self.action_redo)
        self._toolbar.delete_requested.connect(self._view.delete_selected)
        self._toolbar.zoom_in_requested.connect(self._view.zoom_in)
        self._toolbar.zoom_out_requested.connect(self._view.zoom_out)
        self._toolbar.zoom_fit_requested.connect(self._view.zoom_fit_width)
        self._toolbar.zoom_page_requested.connect(self._view.zoom_fit_page)
        self._toolbar.read_mode_requested.connect(self.toggle_read_mode)
        self._toolbar.bangla_toggled.connect(self._on_bangla_toggled)
        self._toolbar.tool_selected.connect(self._on_tool_selected)
        self._view.tool_switched.connect(self._toolbar.set_current_tool)

        # Bangla engine
        self._bangla_engine.mode_changed.connect(self._on_bangla_mode_changed)

        # Undo stack
        self._undo_stack.changed.connect(self._update_undo_redo_ui)

        # Canvas signals
        self._view.page_changed.connect(self._on_page_changed)
        self._view.zoom_changed.connect(self._on_zoom_changed)
        self._view.text_box_added.connect(self._on_text_box_added)
        self._view.annotation_added.connect(self._on_annotation_added)
        self._view.annotation_deleted.connect(self._on_annotation_deleted)

        # Thumbnail panel signals
        self._thumb_panel.page_selected.connect(self._view.go_to_page)
        self._thumb_panel.page_delete_requested.connect(self._on_page_delete_index)
        self._thumb_panel.page_rotate_requested.connect(self._on_page_rotate_index)
        self._thumb_panel.page_insert_requested.connect(self._on_page_insert_index)
        self._thumb_panel.page_reordered.connect(self._on_pages_reordered)

        # Properties panel signals -> View properties
        self._prop_panel.font_changed.connect(lambda f: self._view.update_properties({"font_family": f}))
        self._prop_panel.font_size_changed.connect(lambda s: self._view.update_properties({"font_size": s}))
        self._prop_panel.color_changed.connect(lambda c: self._view.update_properties({"color": c}))
        self._prop_panel.bold_changed.connect(lambda b: self._view.update_properties({"bold": b}))
        self._prop_panel.italic_changed.connect(lambda i: self._view.update_properties({"italic": i}))
        self._prop_panel.underline_changed.connect(lambda u: self._view.update_properties({"underline": u}))
        self._prop_panel.strike_changed.connect(lambda s: self._view.update_properties({"strikethrough": s}))
        self._prop_panel.annotation_type_changed.connect(self._on_annotation_style_changed)
        self._prop_panel.stroke_color_changed.connect(lambda c: self._view.update_properties({"stroke_color": c}))
        self._prop_panel.fill_color_changed.connect(lambda c: self._view.update_properties({"fill_color": c}))
        self._prop_panel.stroke_width_changed.connect(lambda w: self._view.update_properties({"stroke_width": w}))
        self._prop_panel.opacity_changed.connect(lambda o: self._view.update_properties({"opacity": o}))

        # View selection -> Properties panel sync
        self._view.text_box_selected.connect(self._prop_panel.show_text_properties)
        self._view.shape_selected.connect(self._prop_panel.show_shape_properties)
        self._view.annotation_selected.connect(self._prop_panel.show_annotation_properties)
        self._view.image_selected.connect(self._prop_panel.show_image_properties)
        self._view.selection_cleared.connect(self._on_selection_cleared)
        self._view.document_modified.connect(self._mark_modified)

        # Shortcut for Bangla toggle: Ctrl+Space and Ctrl+B
        shortcut_bangla = QAction(self)
        shortcut_bangla.setShortcuts([QKeySequence("Ctrl+Space"), QKeySequence("Ctrl+B")])
        shortcut_bangla.triggered.connect(self._bangla_engine.toggle)
        self.addAction(shortcut_bangla)

        # Global delete shortcuts for active selections
        shortcut_del = QAction(self)
        shortcut_del.setShortcuts([QKeySequence.StandardKey.Delete, QKeySequence("Backspace")])
        shortcut_del.triggered.connect(self._view.delete_selected)
        self.addAction(shortcut_del)

    # ================================================================== #
    #  Slot Handlers
    # ================================================================== #

    def _on_tool_selected(self, tool: Tool) -> None:
        self._view.set_tool(tool)
        self._prop_panel.set_tool(tool)

        # If Image or Signature tool chosen, prompt file dialog immediately
        if tool in (Tool.IMAGE, Tool.SIGNATURE):
            file_filter = "Images (*.png *.jpg *.jpeg *.bmp *.svg);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(self, self._i18n.t("select_image_file"), "", file_filter)
            if path:
                self._view._update_current_page_from_viewport()
                cur_page = self._view._current_page_index
                insert_pos = self._view.get_viewport_center_on_page(cur_page)
                self._view.add_image_at(cur_page, path, insert_pos)
            self._toolbar.set_current_tool(Tool.SELECT)
            self._view.set_tool(Tool.SELECT)

    def _on_selection_cleared(self) -> None:
        if self._toolbar.current_tool == Tool.TEXT:
            self._prop_panel.set_tool(Tool.TEXT)
        else:
            self._prop_panel.show_empty()

    def _on_annotation_style_changed(self, style_name: str) -> None:
        style_tool_map = {
            "highlight": Tool.HIGHLIGHT,
            "underline": Tool.UNDERLINE,
            "strikethrough": Tool.STRIKETHROUGH,
        }
        target_tool = style_tool_map.get(style_name, Tool.HIGHLIGHT)
        self._view.set_tool(target_tool)
        self._view.update_properties({"annotation_type": style_name})

    def _mark_modified(self) -> None:
        self._is_modified = True

    def _on_bangla_toggled(self, active: bool) -> None:
        self._bangla_engine.set_active(active)

    def _on_bangla_mode_changed(self, active: bool) -> None:
        self._toolbar.set_bangla_active(active)
        status_key = "status_bangla_on" if active else "status_bangla_off"
        color = "#4caf50" if active else "#9e9e9e"
        self._status_bangla_label.setText(self._i18n.t(status_key))
        self._status_bangla_label.setStyleSheet(f"color: {color}; font-weight: bold; padding: 0 8px;")

    def _update_undo_redo_ui(self) -> None:
        can_u = self._undo_stack.can_undo
        can_r = self._undo_stack.can_redo
        self._toolbar.update_undo_redo(can_u, can_r)
        self._act_undo.setEnabled(can_u)
        self._act_redo.setEnabled(can_r)

    def _on_page_changed(self, page_index: int) -> None:
        total = self._engine.page_count
        self._status_page_label.setText(
            self._i18n.t("status_page_info", current=page_index + 1, total=max(1, total))
        )
        self._thumb_panel.set_current_page(page_index)

    def _on_zoom_changed(self, zoom: float) -> None:
        self._status_zoom_label.setText(self._i18n.t("status_zoom", zoom=int(zoom * 100)))

    def _on_text_box_added(self, data) -> None:
        cmd = AddTextBoxCommand(self._engine.annotation_manager, data)
        self._undo_stack.push(cmd)

    def _on_annotation_added(self, data) -> None:
        mgr = self._engine.annotation_manager
        name = data.__class__.__name__
        if "Highlight" in name:
            cmd = AddHighlightCommand(mgr, data)
        elif "Shape" in name:
            cmd = AddShapeCommand(mgr, data)
        elif "Freehand" in name:
            cmd = AddFreehandCommand(mgr, data)
        elif "Image" in name:
            cmd = AddImageCommand(mgr, data)
        else:
            return
        self._undo_stack.push(cmd)

    def _on_annotation_deleted(self, ann_id: str) -> None:
        mgr = self._engine.annotation_manager
        tb = mgr.get_text_box(ann_id)
        if tb:
            self._undo_stack.push(RemoveTextBoxCommand(mgr, tb))
            return
        hl = mgr.get_highlight(ann_id)
        if hl:
            self._undo_stack.push(RemoveHighlightCommand(mgr, hl))
            return
        sh = mgr.get_shape(ann_id)
        if sh:
            self._undo_stack.push(RemoveShapeCommand(mgr, sh))
            return
        fh = mgr.get_freehand(ann_id)
        if fh:
            self._undo_stack.push(RemoveFreehandCommand(mgr, fh))
            return
        im = mgr.get_image(ann_id)
        if im:
            self._undo_stack.push(RemoveImageCommand(mgr, im))
            return

    # ================================================================== #
    #  Page Operations
    # ================================================================== #

    def action_delete_page(self) -> None:
        self._on_page_delete_index(self._view._current_page_index)

    def _on_page_delete_index(self, page_index: int) -> None:
        if self._engine.page_count <= 1:
            QMessageBox.warning(self, self._i18n.t("warning"), "Cannot delete the only page in the document.")
            return

        reply = QMessageBox.question(
            self,
            self._i18n.t("confirm"),
            self._i18n.t("confirm_delete_page"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cmd = DeletePageCommand(self._engine.document, page_index)
            self._undo_stack.push(cmd)
            self._mark_modified()
            self._view.load_document(self._engine, preserve_view=True)
            self._thumb_panel.refresh(self._engine)

    def action_rotate_page(self) -> None:
        self._on_page_rotate_index(self._view._current_page_index)

    def _on_page_rotate_index(self, page_index: int) -> None:
        cmd = RotatePageCommand(self._engine.document, page_index, angle=90)
        self._undo_stack.push(cmd)
        self._mark_modified()
        self._view.refresh_page(page_index)
        self._thumb_panel.update_thumbnail(page_index, self._engine)

    def action_insert_blank_page(self) -> None:
        self._on_page_insert_index(self._view._current_page_index)

    def _on_page_insert_index(self, after_index: int) -> None:
        target_idx = after_index + 1
        cmd = InsertBlankPageCommand(self._engine.document, target_idx)
        self._undo_stack.push(cmd)
        self._mark_modified()
        self._view.load_document(self._engine, preserve_view=True)
        self._thumb_panel.refresh(self._engine)

    def _on_pages_reordered(self, new_order: list[int]) -> None:
        cmd = ReorderPagesCommand(self._engine.document, new_order)
        self._undo_stack.push(cmd)
        self._mark_modified()
        self._view.load_document(self._engine, preserve_view=True)
        self._thumb_panel.refresh(self._engine)

    # ================================================================== #
    #  File & Dialog Actions
    # ================================================================== #

    def _show_welcome_screen(self) -> None:
        """Show the professional Welcome Screen and disable document-specific controls."""
        self._stack.setCurrentWidget(self._welcome)
        self._welcome.refresh_recent_files()
        self._thumb_panel.setVisible(False)
        self._prop_panel.setVisible(False)
        self._toolbar._save_action.setEnabled(False)
        self._toolbar._close_action.setEnabled(False)
        self._act_save.setEnabled(False)
        self._act_save_as.setEnabled(False)
        self._act_close.setEnabled(False)
        self.setWindowTitle(self._i18n.t("app_title"))
        self._status_bar.showMessage(self._i18n.t("ready"), 3000)

    def action_close_document(self) -> None:
        """Close current PDF and return to the professional Welcome Screen."""
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                self._i18n.t("confirm"),
                self._i18n.t("confirm_unsaved_changes"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                saved = self.action_save(prompt_overwrite=True)
                if not saved or self._is_modified:
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self._engine.close()
        self._is_modified = False
        self._undo_stack.clear()
        self._show_welcome_screen()

    def action_open(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._i18n.t("select_pdf_files"),
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if file_path:
            self.open_file(file_path)

    def open_file(self, file_path: str) -> None:
        try:
            self._engine.open(file_path)
            RecentFilesManager.add_recent_file(file_path)
            self._undo_stack.clear()
            self._is_modified = False

            # Switch to editor view and display panels first so viewport width is established
            self._thumb_panel.setVisible(True)
            self._prop_panel.setVisible(True)
            self._stack.setCurrentWidget(self._view)

            self._view.load_document(self._engine)
            self._thumb_panel.refresh(self._engine)

            self._toolbar._save_action.setEnabled(True)
            self._toolbar._close_action.setEnabled(True)
            self._act_save.setEnabled(True)
            self._act_save_as.setEnabled(True)
            self._act_close.setEnabled(True)
            self.setWindowTitle(f"{os.path.basename(file_path)} - {self._i18n.t('app_title')}")
            self._status_bar.showMessage(f"Opened: {file_path}", 3000)

            # Re-fit to width once layout geometry has completely settled
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._view.zoom_fit_width)
            QTimer.singleShot(50, self._view.zoom_fit_width)
        except Exception as e:
            logger.error("Failed to open file: %s", e)
            QMessageBox.critical(self, self._i18n.t("error"), f"Failed to open PDF:\n{e}")

    def action_save(self, *args: Any, prompt_overwrite: bool = True) -> bool:
        """Save the document. If saving will overwrite the original PDF file,
        prompts the user with a warning dialog offering Overwrite, Save As, or Cancel.
        Returns True if saved, False otherwise.
        """
        if self._engine.file_path:
            if prompt_overwrite:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle(self._i18n.t("overwrite_warning_title"))
                fname = os.path.basename(self._engine.file_path)
                msg_box.setText(self._i18n.t("overwrite_warning_text", filename=fname))
                msg_box.setInformativeText(self._i18n.t("overwrite_warning_info", path=self._engine.file_path))

                btn_overwrite = msg_box.addButton(
                    self._i18n.t("btn_overwrite"), QMessageBox.ButtonRole.AcceptRole
                )
                btn_save_as = msg_box.addButton(
                    self._i18n.t("btn_save_as"), QMessageBox.ButtonRole.ActionRole
                )
                btn_cancel = msg_box.addButton(QMessageBox.StandardButton.Cancel)

                btn_overwrite.setStyleSheet(
                    "background-color: #dc2626; color: #ffffff; font-weight: 600; padding: 6px 14px; border-radius: 4px;"
                )
                btn_save_as.setStyleSheet(
                    "background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 6px 14px; border-radius: 4px;"
                )
                msg_box.setDefaultButton(btn_save_as)

                msg_box.exec()
                clicked = msg_box.clickedButton()
                if clicked == btn_overwrite:
                    pass  # User explicitly confirmed overwrite
                elif clicked == btn_save_as:
                    return self.action_save_as()
                else:
                    return False  # Canceled

            try:
                self._engine.save()
                RecentFilesManager.add_recent_file(self._engine.file_path)
                self._is_modified = False
                self._status_bar.showMessage(self._i18n.t("saved_successfully", path=self._engine.file_path), 3000)
                return True
            except PermissionError as e:
                logger.error("Save permission denied: %s", e)
                fname = os.path.basename(self._engine.file_path)
                reply = QMessageBox.warning(
                    self,
                    self._i18n.t("warning"),
                    f"Cannot overwrite '{fname}' because the file is currently locked by another program (such as Adobe Acrobat or a web browser) or is read-only.\n\nWould you like to save it with a new name using 'Save As'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return self.action_save_as()
                return False
            except Exception as e:
                if "permission" in str(e).lower() or "cannot remove file" in str(e).lower():
                    logger.error("Save permission denied: %s", e)
                    fname = os.path.basename(self._engine.file_path)
                    reply = QMessageBox.warning(
                        self,
                        self._i18n.t("warning"),
                        f"Cannot overwrite '{fname}' because the file is locked by another program or has restricted permissions.\n\nWould you like to save it with a new name using 'Save As'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        return self.action_save_as()
                    return False
                logger.error("Save failed: %s", e)
                QMessageBox.critical(self, self._i18n.t("error"), f"Failed to save:\n{e}")
                return False
        else:
            return self.action_save_as()

    def action_save_as(self) -> bool:
        suggested = self._engine.file_path or "document.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._i18n.t("save_as"),
            suggested,
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if file_path:
            try:
                self._engine.save_as(file_path)
                RecentFilesManager.add_recent_file(file_path)
                self._is_modified = False
                self.setWindowTitle(f"{os.path.basename(file_path)} - {self._i18n.t('app_title')}")
                self._status_bar.showMessage(self._i18n.t("saved_successfully", path=file_path), 3000)
                return True
            except PermissionError as e:
                logger.error("Save As permission denied: %s", e)
                QMessageBox.critical(
                    self,
                    self._i18n.t("error"),
                    f"Cannot save to '{os.path.basename(file_path)}' (Permission Denied). Please select a different file name or location.",
                )
                return False
            except Exception as e:
                logger.error("Save As failed: %s", e)
                QMessageBox.critical(self, self._i18n.t("error"), f"Failed to save:\n{e}")
                return False
        return False

    def action_export_image(self) -> None:
        dlg = ExportImageDialog(
            page_count=self._engine.page_count,
            current_page=self._view._current_page_index,
            i18n=self._i18n,
            parent=self,
        )
        if dlg.exec():
            settings = dlg.get_settings()
            out_dir = settings["output_dir"]
            fmt = settings["format"].lower()
            dpi = settings["dpi"]

            if not os.path.isdir(out_dir):
                QMessageBox.warning(self, self._i18n.t("warning"), self._i18n.t("no_directory"))
                return

            for p_idx in settings["pages"]:
                out_file = os.path.join(out_dir, f"page_{p_idx + 1}.{fmt}")
                self._engine.export_page_as_image(p_idx, out_file, dpi=dpi)

            self._status_bar.showMessage(self._i18n.t("exported_successfully", path=out_dir), 3000)

    def action_merge_pdfs(self) -> None:
        dlg = MergeDialog(self._i18n, self)
        if dlg.exec():
            files = dlg.get_files()
            if len(files) >= 2:
                out_path, _ = QFileDialog.getSaveFileName(
                    self,
                    self._i18n.t("save_as"),
                    "merged.pdf",
                    "PDF Files (*.pdf)",
                )
                if out_path:
                    PageTools.merge_pdfs(files, out_path)
                    self.open_file(out_path)

    def action_split_pdf(self) -> None:
        dlg = SplitDialog(self._engine.page_count, self._i18n, self)
        if dlg.exec():
            ranges = dlg.get_ranges()
            out_dir = dlg.get_output_dir()
            if ranges and os.path.isdir(out_dir):
                created = PageTools.split_pdf(self._engine.document, ranges, out_dir)
                QMessageBox.information(
                    self,
                    self._i18n.t("split_pdf"),
                    f"Created {len(created)} PDF files in:\n{out_dir}",
                )

    def action_about(self) -> None:
        dlg = AboutDialog(self._i18n, self)
        dlg.exec()

    def action_undo(self) -> None:
        if self._undo_stack.can_undo:
            self._undo_stack.undo()
            self._view.load_document(self._engine, preserve_view=True)
            self._thumb_panel.refresh(self._engine)
            self._status_bar.showMessage("Undone", 2000)

    def action_redo(self) -> None:
        if self._undo_stack.can_redo:
            self._undo_stack.redo()
            self._view.load_document(self._engine, preserve_view=True)
            self._thumb_panel.refresh(self._engine)
            self._status_bar.showMessage("Redone", 2000)

    # ================================================================== #
    #  View Modes: Read Mode & Full Screen
    # ================================================================== #

    def toggle_read_mode(self) -> None:
        """Toggle distraction-free Read Mode hiding toolbars and sidebars."""
        self._is_read_mode = not getattr(self, "_is_read_mode", False)
        if self._is_read_mode:
            self._saved_thumb_visible = self._thumb_panel.isVisible()
            self._saved_prop_visible = self._prop_panel.isVisible()
            self._toolbar.setVisible(False)
            self._thumb_panel.setVisible(False)
            self._prop_panel.setVisible(False)
            self._status_bar.setVisible(False)
            self.menuBar().setVisible(False)

            if not hasattr(self, "_exit_read_btn"):
                self._exit_read_btn = QPushButton("✕ " + self._i18n.t("exit_read_mode") + " (Esc)", self)
                self._exit_read_btn.setStyleSheet(
                    "QPushButton { background: rgba(15, 23, 42, 0.9); color: white; border: 1.5px solid rgba(255,255,255,0.4); border-radius: 18px; padding: 7px 18px; font-weight: 700; font-size: 12px; }"
                    "QPushButton:hover { background: #0284c7; border-color: #38bdf8; }"
                )
                self._exit_read_btn.clicked.connect(self.toggle_read_mode)
            self._position_exit_read_btn()
            self._exit_read_btn.show()
            self._exit_read_btn.raise_()
            self._view.zoom_fit_width()
        else:
            self._toolbar.setVisible(True)
            self._thumb_panel.setVisible(getattr(self, "_saved_thumb_visible", True))
            self._prop_panel.setVisible(getattr(self, "_saved_prop_visible", True))
            self._status_bar.setVisible(True)
            self.menuBar().setVisible(True)
            if hasattr(self, "_exit_read_btn"):
                self._exit_read_btn.hide()
            self._view.zoom_fit_width()

    def _position_exit_read_btn(self) -> None:
        if hasattr(self, "_exit_read_btn") and self._exit_read_btn.isVisible():
            self._exit_read_btn.adjustSize()
            self._exit_read_btn.move(self.width() - self._exit_read_btn.width() - 25, 20)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_exit_read_btn()

    def toggle_full_screen(self) -> None:
        """Toggle Full Screen display."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Window-level key shortcuts."""
        if event.key() == Qt.Key.Key_Escape and getattr(self, "_is_read_mode", False):
            self.toggle_read_mode()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F11:
            self.toggle_full_screen()
            event.accept()
            return
        super().keyPressEvent(event)

    # ================================================================== #
    #  Themes & Translations
    # ================================================================== #

    def toggle_theme(self) -> None:
        self._is_dark_theme = not self._is_dark_theme
        ThemeManager.apply_theme(QApplication.instance(), dark=self._is_dark_theme)
        theme_text = self._i18n.t("theme_light") if self._is_dark_theme else self._i18n.t("theme_dark")
        self._act_theme_toggle.setText(theme_text)

    def set_language(self, language: Language) -> None:
        self._i18n.set_language(language)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self._i18n.t("app_title"))

        # Menus
        self._menu_file.setTitle(self._i18n.t("menu_file"))
        self._act_open.setText(self._i18n.t("open_file"))
        self._act_save.setText(self._i18n.t("save_file"))
        self._act_save_as.setText(self._i18n.t("save_as"))
        self._act_close.setText(self._i18n.t("close_file"))
        self._act_export.setText(self._i18n.t("export_as_image"))
        self._act_exit.setText(self._i18n.t("exit"))

        self._menu_edit.setTitle(self._i18n.t("menu_edit"))
        self._act_undo.setText(self._i18n.t("undo"))
        self._act_redo.setText(self._i18n.t("redo"))
        self._act_del.setText(self._i18n.t("action_delete"))

        self._menu_view.setTitle(self._i18n.t("menu_view"))
        self._act_actual_size.setText(self._i18n.t("zoom_actual_size"))
        self._act_zoom_fit.setText(self._i18n.t("zoom_fit_width"))
        self._act_zoom_page.setText(self._i18n.t("zoom_fit_page"))
        self._act_zoom_height.setText(self._i18n.t("zoom_fit_height"))
        self._act_zoom_in.setText(self._i18n.t("zoom_in"))
        self._act_zoom_out.setText(self._i18n.t("zoom_out"))
        self._act_read_mode.setText(self._i18n.t("read_mode"))
        self._act_full_screen.setText(self._i18n.t("full_screen"))
        theme_text = self._i18n.t("theme_light") if self._is_dark_theme else self._i18n.t("theme_dark")
        self._act_theme_toggle.setText(theme_text)

        self._menu_pages.setTitle(self._i18n.t("menu_pages"))
        self._act_delete_page.setText(self._i18n.t("delete_page"))
        self._act_rotate_page.setText(self._i18n.t("rotate_page"))
        self._act_insert_blank.setText(self._i18n.t("insert_blank_page"))
        self._act_merge.setText(self._i18n.t("merge_pdfs"))
        self._act_split.setText(self._i18n.t("split_pdf"))

        self._menu_lang.setTitle(self._i18n.t("menu_language"))
        self._act_lang_en.setText(self._i18n.t("lang_english"))
        self._act_lang_bn.setText(self._i18n.t("lang_bangla"))

        self._menu_help.setTitle(self._i18n.t("menu_help"))
        self._act_about.setText(self._i18n.t("about"))

        # Toolbar & Panels
        self._toolbar.update_translations(self._i18n)
        self._thumb_panel.update_translations(self._i18n)
        self._prop_panel.update_translations(self._i18n)

        # Status
        self._on_page_changed(self._view._current_page_index)
        self._on_bangla_mode_changed(self._bangla_engine.is_active)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_modified:
            reply = QMessageBox.question(
                self,
                self._i18n.t("confirm"),
                self._i18n.t("confirm_unsaved_changes"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                saved = self.action_save(prompt_overwrite=True)
                if saved and not self._is_modified:
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

