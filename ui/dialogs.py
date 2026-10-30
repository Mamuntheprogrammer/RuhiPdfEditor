"""
Dialog windows for the PDF Editor.

Provides dialogs for:
* Merging multiple PDF files
* Splitting a PDF by page ranges
* Exporting pages as images
* About / credits
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ui.i18n import I18n


# ====================================================================== #
#  Merge Dialog
# ====================================================================== #

class MergeDialog(QDialog):
    """Dialog for merging multiple PDF files.

    Users add PDF files to a list, reorder them, and confirm.
    """

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setWindowTitle(i18n.t("merge_pdfs"))
        self.setMinimumSize(520, 400)

        layout = QVBoxLayout(self)

        # Instructions
        layout.addWidget(QLabel(i18n.t("merge_instructions")))

        # File list
        self._file_list = QListWidget()
        layout.addWidget(self._file_list)

        # Buttons to manage the list
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton(i18n.t("add"))
        self._remove_btn = QPushButton(i18n.t("remove"))
        self._up_btn = QPushButton(i18n.t("move_up"))
        self._down_btn = QPushButton(i18n.t("move_down"))

        self._add_btn.clicked.connect(self._add_files)
        self._remove_btn.clicked.connect(self._remove_selected)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)

        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._up_btn)
        btn_row.addWidget(self._down_btn)
        layout.addLayout(btn_row)

        # OK / Cancel
        ok_cancel = QHBoxLayout()
        ok_cancel.addStretch()
        self._ok_btn = QPushButton(i18n.t("ok"))
        self._ok_btn.setProperty("primary", True)
        self._ok_btn.clicked.connect(self.accept)
        self._cancel_btn = QPushButton(i18n.t("cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        ok_cancel.addWidget(self._ok_btn)
        ok_cancel.addWidget(self._cancel_btn)
        layout.addLayout(ok_cancel)

    # ---- List management ---- #

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self._i18n.t("select_pdf_files"),
            "",
            "PDF Files (*.pdf)",
        )
        for p in paths:
            self._file_list.addItem(p)

    def _remove_selected(self) -> None:
        row = self._file_list.currentRow()
        if row >= 0:
            self._file_list.takeItem(row)

    def _move_up(self) -> None:
        row = self._file_list.currentRow()
        if row > 0:
            item = self._file_list.takeItem(row)
            self._file_list.insertItem(row - 1, item)
            self._file_list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._file_list.currentRow()
        if row < self._file_list.count() - 1:
            item = self._file_list.takeItem(row)
            self._file_list.insertItem(row + 1, item)
            self._file_list.setCurrentRow(row + 1)

    # ---- Public API ---- #

    def get_files(self) -> list[str]:
        """Return the ordered list of PDF file paths.

        Returns:
            List of absolute paths to PDF files.
        """
        return [
            self._file_list.item(i).text()
            for i in range(self._file_list.count())
        ]


# ====================================================================== #
#  Split Dialog
# ====================================================================== #

class SplitDialog(QDialog):
    """Dialog for splitting a PDF by page ranges.

    Users specify ranges such as ``1-3, 5, 7-9`` and choose an output
    directory.
    """

    def __init__(self, page_count: int, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._page_count = page_count
        self.setWindowTitle(i18n.t("split_pdf"))
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Info label
        info = QLabel(
            i18n.t("split_info").replace("{pages}", str(page_count))
        )
        layout.addWidget(info)

        # Range input
        range_group = QGroupBox(i18n.t("page_ranges"))
        rg_layout = QVBoxLayout(range_group)
        rg_layout.addWidget(
            QLabel(i18n.t("split_range_hint"))
        )
        self._range_edit = QLineEdit()
        self._range_edit.setPlaceholderText("1-3, 5, 7-9")
        rg_layout.addWidget(self._range_edit)
        layout.addWidget(range_group)

        # Output directory
        dir_group = QGroupBox(i18n.t("output_directory"))
        dg_layout = QHBoxLayout(dir_group)
        self._dir_edit = QLineEdit()
        self._dir_edit.setReadOnly(True)
        self._browse_btn = QPushButton(i18n.t("browse"))
        self._browse_btn.clicked.connect(self._browse_dir)
        dg_layout.addWidget(self._dir_edit)
        dg_layout.addWidget(self._browse_btn)
        layout.addWidget(dir_group)

        # OK / Cancel
        ok_cancel = QHBoxLayout()
        ok_cancel.addStretch()
        self._ok_btn = QPushButton(i18n.t("ok"))
        self._ok_btn.setProperty("primary", True)
        self._ok_btn.clicked.connect(self._validate_and_accept)
        self._cancel_btn = QPushButton(i18n.t("cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        ok_cancel.addWidget(self._ok_btn)
        ok_cancel.addWidget(self._cancel_btn)
        layout.addLayout(ok_cancel)

    def _browse_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, self._i18n.t("select_output_directory")
        )
        if directory:
            self._dir_edit.setText(directory)

    def _validate_and_accept(self) -> None:
        """Parse the range text, validate, and accept if valid."""
        try:
            ranges = self.get_ranges()
            if not ranges:
                raise ValueError("empty")
        except ValueError:
            QMessageBox.warning(
                self,
                self._i18n.t("invalid_range"),
                self._i18n.t("split_range_error"),
            )
            return

        if not self._dir_edit.text():
            QMessageBox.warning(
                self,
                self._i18n.t("no_directory"),
                self._i18n.t("select_output_directory"),
            )
            return

        self.accept()

    # ---- Public API ---- #

    def get_ranges(self) -> list[tuple[int, int]]:
        """Parse the range text and return a list of ``(start, end)`` tuples.

        Page numbers are 0-based in the returned tuples (user enters 1-based).

        Returns:
            List of (start_page_0based, end_page_0based) tuples.

        Raises:
            ValueError: If the range text is malformed.
        """
        text = self._range_edit.text().strip()
        if not text:
            raise ValueError("Empty range")

        result: list[tuple[int, int]] = []
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start = int(start_s.strip()) - 1
                end = int(end_s.strip()) - 1
            else:
                start = end = int(part.strip()) - 1

            if start < 0 or end < 0 or start >= self._page_count or end >= self._page_count:
                raise ValueError(f"Page out of range: {part}")
            if start > end:
                raise ValueError(f"Invalid range: {part}")
            result.append((start, end))
        return result

    def get_output_dir(self) -> str:
        """Return the chosen output directory.

        Returns:
            Absolute path to the output directory.
        """
        return self._dir_edit.text()


# ====================================================================== #
#  Export Image Dialog
# ====================================================================== #

class ExportImageDialog(QDialog):
    """Dialog for exporting PDF pages as images.

    Users choose which pages to export, DPI, format, and output path.
    """

    def __init__(
        self,
        page_count: int,
        current_page: int,
        i18n: I18n,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._page_count = page_count
        self._current_page = current_page
        self.setWindowTitle(i18n.t("export_as_image"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # Page selection
        page_group = QGroupBox(i18n.t("page_selection"))
        pg_layout = QVBoxLayout(page_group)
        self._current_rb = QRadioButton(
            i18n.t("current_page_num").replace("{page}", str(current_page + 1))
        )
        self._current_rb.setChecked(True)
        self._all_rb = QRadioButton(i18n.t("all_pages"))
        self._range_rb = QRadioButton(i18n.t("page_range"))
        self._range_edit = QLineEdit()
        self._range_edit.setPlaceholderText("1-3, 5")
        self._range_edit.setEnabled(False)
        self._range_rb.toggled.connect(self._range_edit.setEnabled)

        pg_layout.addWidget(self._current_rb)
        pg_layout.addWidget(self._all_rb)
        range_row = QHBoxLayout()
        range_row.addWidget(self._range_rb)
        range_row.addWidget(self._range_edit)
        pg_layout.addLayout(range_row)
        layout.addWidget(page_group)

        # Settings
        settings_group = QGroupBox(i18n.t("settings"))
        sg_layout = QVBoxLayout(settings_group)

        # DPI
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("DPI:"))
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 1200)
        self._dpi_spin.setValue(300)
        self._dpi_spin.setSingleStep(150)
        dpi_row.addWidget(self._dpi_spin)
        sg_layout.addLayout(dpi_row)

        # Format
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel(i18n.t("format")))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG", "JPG"])
        fmt_row.addWidget(self._format_combo)
        sg_layout.addLayout(fmt_row)

        layout.addWidget(settings_group)

        # Output path
        out_group = QGroupBox(i18n.t("output_directory"))
        og_layout = QHBoxLayout(out_group)
        self._output_edit = QLineEdit()
        self._output_edit.setReadOnly(True)
        self._browse_btn = QPushButton(i18n.t("browse"))
        self._browse_btn.clicked.connect(self._browse_output)
        og_layout.addWidget(self._output_edit)
        og_layout.addWidget(self._browse_btn)
        layout.addWidget(out_group)

        # OK / Cancel
        ok_cancel = QHBoxLayout()
        ok_cancel.addStretch()
        self._ok_btn = QPushButton(i18n.t("ok"))
        self._ok_btn.setProperty("primary", True)
        self._ok_btn.clicked.connect(self._validate_and_accept)
        self._cancel_btn = QPushButton(i18n.t("cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        ok_cancel.addWidget(self._ok_btn)
        ok_cancel.addWidget(self._cancel_btn)
        layout.addLayout(ok_cancel)

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, self._i18n.t("select_output_directory")
        )
        if directory:
            self._output_edit.setText(directory)

    def _validate_and_accept(self) -> None:
        if not self._output_edit.text():
            QMessageBox.warning(
                self,
                self._i18n.t("no_directory"),
                self._i18n.t("select_output_directory"),
            )
            return
        self.accept()

    # ---- Public API ---- #

    def get_settings(self) -> dict:
        """Return the export settings as a dictionary.

        Returns:
            Dictionary with keys:

            * ``pages`` – list of 0-based page indices to export
            * ``dpi`` – integer DPI
            * ``format`` – ``'PNG'`` or ``'JPG'``
            * ``output_dir`` – absolute directory path
        """
        pages: list[int] = []
        if self._current_rb.isChecked():
            pages = [self._current_page]
        elif self._all_rb.isChecked():
            pages = list(range(self._page_count))
        elif self._range_rb.isChecked():
            text = self._range_edit.text().strip()
            for part in text.split(","):
                part = part.strip()
                if "-" in part:
                    s, e = part.split("-", 1)
                    start = max(0, int(s.strip()) - 1)
                    end = min(self._page_count - 1, int(e.strip()) - 1)
                    pages.extend(range(start, end + 1))
                else:
                    idx = int(part.strip()) - 1
                    if 0 <= idx < self._page_count:
                        pages.append(idx)

        return {
            "pages": pages,
            "dpi": self._dpi_spin.value(),
            "format": self._format_combo.currentText(),
            "output_dir": self._output_edit.text(),
        }


# ====================================================================== #
#  About Dialog
# ====================================================================== #

class AboutDialog(QDialog):
    """About dialog showing application info and credits."""

    def __init__(self, i18n: I18n, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setWindowTitle(i18n.t("about"))
        self.setFixedSize(420, 380)

        layout = QVBoxLayout(self)

        # App title
        title = QLabel(i18n.t("app_title"))
        title_font = title.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Version
        version = QLabel(i18n.t("version").replace("{ver}", "1.0.0"))
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(12)

        # Description
        desc = QTextBrowser()
        desc.setOpenExternalLinks(True)
        desc.setHtml(
            f"<p>{i18n.t('about_description')}</p>"
            "<hr/>"
            f"<p><b>{i18n.t('credits')}:</b></p>"
            "<ul>"
            f"<li>PySide6 (Qt for Python)</li>"
            f"<li>PyMuPDF (fitz)</li>"
            f"<li>Noto Sans Bengali {i18n.t('font')}</li>"
            f"<li>HarfBuzz {i18n.t('text_shaping')}</li>"
            "</ul>"
            f"<p>{i18n.t('license_info')}</p>"
        )
        layout.addWidget(desc)

        # Close button
        close_btn = QPushButton(i18n.t("close"))
        close_btn.clicked.connect(self.accept)
        close_btn.setProperty("primary", True)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


# ====================================================================== #
#  Multi-Line Text Dialog
# ====================================================================== #

class MultiLineTextDialog(QDialog):
    """Modern multi-line text input dialog with Enter for newline, live original text, and Bangla phonetic preview."""

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Text Editor",
        initial_text: str = "",
        bangla_engine=None,
        i18n: I18n | None = None,
        initial_bangla_mode: bool | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 260)
        self._bangla_engine = bangla_engine
        self._i18n = i18n

        # Explicitly disable global Bangla event filter on this dialog and all its children
        self.setProperty("no_bangla_filter", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        prompt = i18n.t("tool_text") if i18n else "Text"
        self._prompt = prompt
        self._label = QLabel(f"{prompt}:")
        self._label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(self._label)

        import unicodedata
        clean_initial = unicodedata.normalize("NFC", initial_text) if initial_text else ""

        self.text_edit = QPlainTextEdit()
        # Mark both the text edit and its viewport to bypass eventFilter buffering
        self.text_edit.setProperty("no_bangla_filter", True)
        if self.text_edit.viewport():
            self.text_edit.viewport().setProperty("no_bangla_filter", True)
        self.text_edit.setPlainText(clean_initial)
        self.text_edit.setPlaceholderText("Type your text here... (Press Enter for a new line)")
        self.text_edit.setStyleSheet(
            "QPlainTextEdit { font-family: 'Noto Sans Bengali', 'SolaimanLipi', 'Kalpurush', 'Segoe UI', Arial, sans-serif; font-size: 15px; padding: 8px; border: 1.5px solid #cbd5e1; border-radius: 6px; background: #ffffff; color: #0f172a; }"
            "QPlainTextEdit:focus { border: 1.5px solid #0284c7; }"
        )
        layout.addWidget(self.text_edit, 1)

        # Bangla live preview card (shows transliterated Bangla text ONLY when phonetic is enabled)
        self.preview_card = QFrame()
        self.preview_card.setObjectName("BanglaPreviewCard")
        self.preview_card.setProperty("no_bangla_filter", True)
        self.preview_card.setStyleSheet(
            "#BanglaPreviewCard { background: #f8fafc; border: 1px solid #0284c7; border-radius: 6px; padding: 8px; }"
        )
        preview_vbox = QVBoxLayout(self.preview_card)
        preview_vbox.setContentsMargins(10, 8, 10, 8)
        preview_vbox.setSpacing(4)

        prev_header = QLabel("লাইভ বাংলা রূপান্তর (Live Bangla Transliteration):")
        prev_header.setStyleSheet("color: #0284c7; font-weight: 700; font-size: 12px;")
        preview_vbox.addWidget(prev_header)

        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview_label.setStyleSheet("font-family: 'Noto Sans Bengali', sans-serif; font-size: 15px; color: #0f172a; padding: 2px 0;")
        preview_vbox.addWidget(self.preview_label)

        self.preview_card.setVisible(False)
        layout.addWidget(self.preview_card)

        # Bottom row with Bangla toggle if available and shortcut hint
        bottom_row = QHBoxLayout()
        if self._bangla_engine:
            self._bangla_cb = QCheckBox("Bangla Phonetic (Avro)")
            use_bangla = bool(initial_bangla_mode)
            self._bangla_cb.setChecked(use_bangla)
            self._bangla_cb.toggled.connect(self._on_bangla_toggled)
            bottom_row.addWidget(self._bangla_cb)
            if use_bangla:
                self._on_bangla_toggled(True)
        else:
            self._bangla_cb = None

        bottom_row.addStretch()
        tip = QLabel("Enter: new line  |  Ctrl+Enter: save")
        tip.setStyleSheet("color: #64748b; font-size: 11px;")
        bottom_row.addWidget(tip)
        layout.addLayout(bottom_row)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(i18n.t("cancel") if i18n else "Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton(i18n.t("ok") if i18n else "OK")
        self.btn_ok.setDefault(True)
        self.btn_ok.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: white; font-weight: 600; padding: 6px 18px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #0369a1; }"
        )
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

        # Connect text changed to update preview live
        self.text_edit.textChanged.connect(self._update_preview)
        self._update_preview()

        # Set initial focus directly into text editor
        self.text_edit.setFocus()
        if initial_text:
            self.text_edit.selectAll()

    def _on_bangla_toggled(self, checked: bool) -> None:
        self.preview_card.setVisible(checked)
        if checked:
            self._label.setText("Original Phonetic Text (ইংরেজি বর্ণে টাইপ করুন - যেমন: amra shobai raja):")
        else:
            self._label.setText(f"{self._prompt}:")
        self._update_preview()
        self.adjustSize()

    def _update_preview(self) -> None:
        is_bangla = bool(self._bangla_cb and self._bangla_cb.isChecked() and self._bangla_engine)
        self.preview_card.setVisible(is_bangla)
        if is_bangla:
            self._label.setText("Original Phonetic Text (ইংরেজি বর্ণে টাইপ করুন - যেমন: amra shobai raja):")
            raw_text = self.text_edit.toPlainText()
            if raw_text.strip():
                converted = self._bangla_engine.transliterate(raw_text)
                self.preview_label.setText(converted)
            else:
                self.preview_label.setText("(টাইপ করুন বাংলা দেখতে...)")
        else:
            self._label.setText(f"{self._prompt}:")

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        wh = self.windowHandle()
        if wh:
            wh.setProperty("no_bangla_filter", True)
        QTimer.singleShot(0, self.text_edit.setFocus)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.accept()
            return
        super().keyPressEvent(event)

    def get_text(self) -> str:
        import unicodedata
        text = self.text_edit.toPlainText()
        if self._bangla_cb and self._bangla_cb.isChecked() and self._bangla_engine:
            converted = self._bangla_engine.transliterate(text)
            return unicodedata.normalize("NFC", converted)
        return unicodedata.normalize("NFC", text)
