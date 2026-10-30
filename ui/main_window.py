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
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
)

from core.annotations import (
    AddFreehandCommand,
    AddHighlightCommand,
    AddImageCommand,
    AddShapeCommand,
    AddTextBoxCommand,
    RemoveTextBoxCommand,
)
from core.bangla_input import BanglaPhoneticEngine
from core.page_tools import DeletePageCommand, PageTools, RotatePageCommand
from core.pdf_engine import PdfEngine
from core.undo_redo import UndoStack
from ui.dialogs import AboutDialog, ExportImageDialog, MergeDialog, SplitDialog
from ui.i18n import I18n, Language
from ui.pdf_view import PdfView
from ui.properties_panel import PropertiesPanel
from ui.themes import ThemeManager
from ui.thumbnail_panel import ThumbnailPanel
from ui.toolbar import EditorToolBar, Tool

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for the PDF Editor."""

    def __init__(self) -> None:
        super().__init__()

        # 1. Core Model & Engines
        self._engine = PdfEngine()
        self._undo_stack = UndoStack()
        self._bangla_engine = BanglaPhoneticEngine(self)
        self._i18n = I18n(Language.ENGLISH)
        self._is_dark_theme = False
        self._is_modified = False

        # 2. Setup Central Canvas
        self._view = PdfView(self)
        self._view.set_dependencies(self._engine, self._bangla_engine, self._i18n)
        self.setCentralWidget(self._view)

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

        # 8. Start with new document
        self._engine.create_new()
        self._view.load_document(self._engine)
        self._thumb_panel.refresh(self._engine)

        # Apply Light Theme by default
        ThemeManager.apply_theme(QApplication.instance(), dark=False)
        self.retranslate_ui()

        self.resize(1360, 850)
        logger.info("MainWindow initialized successfully.")

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
        self._menu_file.addSeparator()
        self._act_export = self._menu_file.addAction(self._i18n.t("export_as_image"), self.action_export_image)
        self._menu_file.addSeparator()
        self._act_exit = self._menu_file.addAction(self._i18n.t("exit"), self.close, QKeySequence.StandardKey.Quit)

        # --- Edit Menu ---
        self._menu_edit = mb.addMenu(self._i18n.t("menu_edit"))
        self._act_undo = self._menu_edit.addAction(self._i18n.t("undo"), self.action_undo, QKeySequence.StandardKey.Undo)
        self._act_redo = self._menu_edit.addAction(self._i18n.t("redo"), self.action_redo, QKeySequence.StandardKey.Redo)
        self._act_del = self._menu_edit.addAction(self._i18n.t("action_delete"), self._view.delete_selected, QKeySequence.StandardKey.Delete)

        # --- View Menu ---
        self._menu_view = mb.addMenu(self._i18n.t("menu_view"))
        self._act_zoom_in = self._menu_view.addAction(self._i18n.t("zoom_in"), self._view.zoom_in, QKeySequence.StandardKey.ZoomIn)
        self._act_zoom_out = self._menu_view.addAction(self._i18n.t("zoom_out"), self._view.zoom_out, QKeySequence.StandardKey.ZoomOut)
        self._act_zoom_fit = self._menu_view.addAction(self._i18n.t("zoom_fit"), self._view.zoom_fit_width, QKeySequence("Ctrl+0"))
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
        self._toolbar.undo_requested.connect(self.action_undo)
        self._toolbar.redo_requested.connect(self.action_redo)
        self._toolbar.delete_requested.connect(self._view.delete_selected)
        self._toolbar.zoom_in_requested.connect(self._view.zoom_in)
        self._toolbar.zoom_out_requested.connect(self._view.zoom_out)
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
        self._prop_panel.stroke_color_changed.connect(lambda c: self._view.update_properties({"stroke_color": c}))
        self._prop_panel.fill_color_changed.connect(lambda c: self._view.update_properties({"fill_color": c}))
        self._prop_panel.stroke_width_changed.connect(lambda w: self._view.update_properties({"stroke_width": w}))
        self._prop_panel.opacity_changed.connect(lambda o: self._view.update_properties({"opacity": o}))

        # View selection -> Properties panel sync
        self._view.text_box_selected.connect(self._prop_panel.show_text_properties)
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
                cur_page = self._view._current_page_index
                self._view.add_image_at(cur_page, path, (100.0, 100.0))
            self._toolbar.set_current_tool(Tool.SELECT)
            self._view.set_tool(Tool.SELECT)

    def _on_selection_cleared(self) -> None:
        if self._toolbar.current_tool == Tool.TEXT:
            self._prop_panel.set_tool(Tool.TEXT)
        else:
            self._prop_panel.show_empty()

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
        # Check text box
        tb = mgr.get_text_box(ann_id)
        if tb:
            self._undo_stack.push(RemoveTextBoxCommand(mgr, tb))
        else:
            mgr.remove_highlight(ann_id)
            mgr.remove_shape(ann_id)
            mgr.remove_freehand(ann_id)
            mgr.remove_image(ann_id)

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
            self._view.load_document(self._engine)
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
        PageTools.insert_blank_page(self._engine.document, target_idx)
        self._mark_modified()
        self._view.load_document(self._engine)
        self._thumb_panel.refresh(self._engine)

    def _on_pages_reordered(self, new_order: list[int]) -> None:
        PageTools.reorder_pages(self._engine.document, new_order)
        self._mark_modified()
        self._view.load_document(self._engine)
        self._thumb_panel.refresh(self._engine)

    # ================================================================== #
    #  File & Dialog Actions
    # ================================================================== #

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
            self._undo_stack.clear()
            self._is_modified = False
            self._view.load_document(self._engine)
            self._thumb_panel.refresh(self._engine)
            self.setWindowTitle(f"{os.path.basename(file_path)} - {self._i18n.t('app_title')}")
            self._status_bar.showMessage(f"Opened: {file_path}", 3000)
        except Exception as e:
            logger.error("Failed to open file: %s", e)
            QMessageBox.critical(self, self._i18n.t("error"), f"Failed to open PDF:\n{e}")

    def action_save(self) -> None:
        if self._engine.file_path:
            try:
                self._engine.save()
                self._is_modified = False
                self._status_bar.showMessage(self._i18n.t("saved_successfully", path=self._engine.file_path), 3000)
            except Exception as e:
                logger.error("Save failed: %s", e)
                QMessageBox.critical(self, self._i18n.t("error"), f"Failed to save:\n{e}")
        else:
            self.action_save_as()

    def action_save_as(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._i18n.t("save_as"),
            "document.pdf",
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if file_path:
            try:
                self._engine.save_as(file_path)
                self._is_modified = False
                self.setWindowTitle(f"{os.path.basename(file_path)} - {self._i18n.t('app_title')}")
                self._status_bar.showMessage(self._i18n.t("saved_successfully", path=file_path), 3000)
            except Exception as e:
                logger.error("Save As failed: %s", e)
                QMessageBox.critical(self, self._i18n.t("error"), f"Failed to save:\n{e}")

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
        self._undo_stack.undo()
        self._view.load_document(self._engine)
        self._thumb_panel.refresh(self._engine)

    def action_redo(self) -> None:
        self._undo_stack.redo()
        self._view.load_document(self._engine)
        self._thumb_panel.refresh(self._engine)

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
        self._act_export.setText(self._i18n.t("export_as_image"))
        self._act_exit.setText(self._i18n.t("exit"))

        self._menu_edit.setTitle(self._i18n.t("menu_edit"))
        self._act_undo.setText(self._i18n.t("undo"))
        self._act_redo.setText(self._i18n.t("redo"))
        self._act_del.setText(self._i18n.t("action_delete"))

        self._menu_view.setTitle(self._i18n.t("menu_view"))
        self._act_zoom_in.setText(self._i18n.t("zoom_in"))
        self._act_zoom_out.setText(self._i18n.t("zoom_out"))
        self._act_zoom_fit.setText(self._i18n.t("zoom_fit"))
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
                self.action_save()
                if not self._is_modified:
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

