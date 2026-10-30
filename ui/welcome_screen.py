"""
Welcome / Home Screen for RuhiPdf Editor.

Displays a modern drag-and-drop file opening zone and a history
of the last 10 edited/opened PDF documents.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QDateTime, QFileInfo, QSettings, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QDragEnterEvent, QDropEvent, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ui.i18n import I18n


class RecentFilesManager:
    """Manages persistent history of the last 10 edited/opened files via QSettings."""

    MAX_RECENT = 10
    SETTINGS_KEY = "RecentFiles/History"

    @classmethod
    def get_recent_files(cls) -> list[dict]:
        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        raw = settings.value(cls.SETTINGS_KEY, [])
        if not isinstance(raw, list):
            return []
        valid_entries = []
        for item in raw:
            if isinstance(item, dict) and "path" in item:
                valid_entries.append(item)
        return valid_entries[: cls.MAX_RECENT]

    @classmethod
    def add_recent_file(cls, file_path: str) -> None:
        if not file_path:
            return
        abs_path = os.path.abspath(file_path)
        existing = cls.get_recent_files()

        # Remove existing if already in list
        filtered = [f for f in existing if os.path.abspath(f.get("path", "")) != abs_path]

        file_name = os.path.basename(abs_path)
        file_size_str = ""
        try:
            sz = os.path.getsize(abs_path)
            if sz < 1024:
                file_size_str = f"{sz} B"
            elif sz < 1024 * 1024:
                file_size_str = f"{sz / 1024:.1f} KB"
            else:
                file_size_str = f"{sz / (1024 * 1024):.1f} MB"
        except OSError:
            pass

        now_str = datetime.now().strftime("%b %d, %Y - %I:%M %p")
        new_entry = {
            "path": abs_path,
            "name": file_name,
            "date": now_str,
            "size": file_size_str,
        }

        # Put newest at the front, limit to MAX_RECENT
        updated = [new_entry] + filtered
        updated = updated[: cls.MAX_RECENT]

        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        settings.setValue(cls.SETTINGS_KEY, updated)

    @classmethod
    def remove_recent_file(cls, file_path: str) -> None:
        abs_path = os.path.abspath(file_path)
        existing = cls.get_recent_files()
        filtered = [f for f in existing if os.path.abspath(f.get("path", "")) != abs_path]
        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        settings.setValue(cls.SETTINGS_KEY, filtered)

    @classmethod
    def clear_recent_files(cls) -> None:
        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        settings.setValue(cls.SETTINGS_KEY, [])


class DragDropZone(QFrame):
    """Modern Drag and Drop card for opening PDF files."""

    file_dropped = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DragDropZone")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._is_drag_over = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Upload / PDF icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_icon_path = Path(__file__).parent.parent / "icons" / "app_icon.png"
        if app_icon_path.exists():
            pix = QPixmap(str(app_icon_path)).scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("📄")
            icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)

        # Main prompt
        title = QLabel("Drag & Drop PDF files here to edit")
        title.setObjectName("DropZoneTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0284c7;")
        layout.addWidget(title)

        # Subtitle / Browse button
        sub_layout = QHBoxLayout()
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_browse = QPushButton("📂  Browse & Open PDF...")
        self.btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #0369a1);
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                padding: 9px 24px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #0284c7;
            }
            QPushButton:pressed {
                background: #0369a1;
            }
        """)
        self.btn_browse.clicked.connect(self._browse_file)
        sub_layout.addWidget(self.btn_browse)
        layout.addLayout(sub_layout)

        hint = QLabel("Supports single & multi-page PDF documents with text, images, and complex Bangla fonts")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("font-size: 11px; color: #64748b; margin-top: 4px;")
        layout.addWidget(hint)

        self._update_style()

    def _update_style(self) -> None:
        if self._is_drag_over:
            self.setStyleSheet("""
                #DragDropZone {
                    background: rgba(2, 132, 199, 0.12);
                    border: 2.5px dashed #0284c7;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                #DragDropZone {
                    background: rgba(248, 250, 252, 0.95);
                    border: 2px dashed #94a3b8;
                    border-radius: 12px;
                }
                #DragDropZone:hover {
                    background: rgba(2, 132, 199, 0.05);
                    border-color: #0284c7;
                }
            """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse_file()
        super().mousePressEvent(event)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF Document - RuhiPdf Editor",
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if path:
            self.file_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    self._is_drag_over = True
                    self._update_style()
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._is_drag_over = False
        self._update_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._is_drag_over = False
        self._update_style()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if local_path.lower().endswith(".pdf") and os.path.isfile(local_path):
                    event.acceptProposedAction()
                    self.file_dropped.emit(local_path)
                    return
        event.ignore()


class RecentFileCard(QFrame):
    """Interactive card row for a single recent file entry."""

    clicked = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, file_info: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_path = file_info.get("path", "")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("RecentFileCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # PDF Badge icon
        badge = QLabel("PDF")
        badge.setStyleSheet("""
            background: #ef4444;
            color: #ffffff;
            font-weight: 800;
            font-size: 10px;
            padding: 3px 6px;
            border-radius: 4px;
        """)
        layout.addWidget(badge)

        # File info layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(file_info.get("name", "Document.pdf"))
        name_label.setStyleSheet("font-weight: 700; font-size: 13px; color: #0f172a;")
        info_layout.addWidget(name_label)

        sub_info = QLabel(self.file_path)
        sub_info.setStyleSheet("font-size: 11px; color: #64748b;")
        info_layout.addWidget(sub_info)

        layout.addLayout(info_layout, 1)

        # Timestamp and size
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(2)
        meta_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        date_label = QLabel(file_info.get("date", ""))
        date_label.setStyleSheet("font-size: 11px; color: #64748b;")
        meta_layout.addWidget(date_label)

        size_label = QLabel(file_info.get("size", ""))
        size_label.setStyleSheet("font-size: 10px; color: #94a3b8;")
        meta_layout.addWidget(size_label)

        layout.addLayout(meta_layout)

        # Remove from history button
        btn_del = QPushButton("✕")
        btn_del.setToolTip("Remove from history")
        btn_del.setFixedSize(22, 22)
        btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 12px;
                font-weight: 700;
                border-radius: 11px;
            }
            QPushButton:hover {
                background: #fee2e2;
                color: #ef4444;
            }
        """)
        btn_del.clicked.connect(lambda: self.remove_requested.emit(self.file_path))
        layout.addWidget(btn_del)

        self.setStyleSheet("""
            #RecentFileCard {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            #RecentFileCard:hover {
                background: #f8fafc;
                border-color: #0284c7;
            }
        """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)


class WelcomeScreen(QWidget):
    """Professional Welcome & Home View with Drag/Drop and Last 10 Recent Files History."""

    file_selected = Signal(str)

    def __init__(self, i18n: Optional[I18n] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setObjectName("WelcomeScreen")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for clean responsive layout on smaller displays
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 30, 40, 40)
        content_layout.setSpacing(24)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ---- 1. App Header ---- #
        header_box = QVBoxLayout()
        header_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.setSpacing(6)

        title_lbl = QLabel("RuhiPdf Editor")
        title_lbl.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.5px;
        """)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(title_lbl)

        sub_lbl = QLabel("Professional Desktop PDF Editor • Bangla & Multilingual Support • Offline & Vector Sharp")
        sub_lbl.setStyleSheet("font-size: 13px; color: #64748b;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(sub_lbl)

        content_layout.addLayout(header_box)

        # ---- 2. Drag & Drop Zone ---- #
        self.drop_zone = DragDropZone(content_widget)
        self.drop_zone.file_dropped.connect(self._on_file_chosen)
        self.drop_zone.setMaximumWidth(820)
        content_layout.addWidget(self.drop_zone, alignment=Qt.AlignmentFlag.AlignCenter)

        # ---- 3. Recent Files Section ---- #
        recent_box = QVBoxLayout()
        recent_box.setSpacing(10)
        recent_box.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        recent_header_widget = QWidget()
        recent_header_widget.setFixedWidth(820)
        recent_header = QHBoxLayout(recent_header_widget)
        recent_header.setContentsMargins(0, 0, 0, 0)

        recent_title = QLabel("📑  Recent Files (Last 10)")
        recent_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #334155;")
        recent_header.addWidget(recent_title)

        recent_header.addStretch()

        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_clear_history.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #ef4444;
            }
        """)
        self.btn_clear_history.clicked.connect(self._clear_history)
        recent_header.addWidget(self.btn_clear_history)

        recent_box.addWidget(recent_header_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Container for recent file items
        self.recent_container = QVBoxLayout()
        self.recent_container.setSpacing(8)
        recent_box.addLayout(self.recent_container)

        content_layout.addLayout(recent_box)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.refresh_recent_files()

    def refresh_recent_files(self) -> None:
        """Reload and display the recent files history."""
        # Clear existing rows
        while self.recent_container.count() > 0:
            item = self.recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent_files = RecentFilesManager.get_recent_files()

        if not recent_files:
            self.btn_clear_history.setVisible(False)
            empty_lbl = QLabel("No recent files yet. Drag & drop a PDF above or click browse to start editing!")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("""
                color: #94a3b8;
                font-size: 12px;
                padding: 24px;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px dashed #cbd5e1;
            """)
            empty_lbl.setFixedWidth(820)
            self.recent_container.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            return

        self.btn_clear_history.setVisible(True)
        for finfo in recent_files:
            card = RecentFileCard(finfo)
            card.setFixedWidth(820)
            card.clicked.connect(self._on_file_chosen)
            card.remove_requested.connect(self._on_remove_item)
            self.recent_container.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_file_chosen(self, path: str) -> None:
        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file could not be found at:\n{path}\n\nIt may have been moved or deleted.",
            )
            RecentFilesManager.remove_recent_file(path)
            self.refresh_recent_files()
            return
        self.file_selected.emit(path)

    def _on_remove_item(self, path: str) -> None:
        RecentFilesManager.remove_recent_file(path)
        self.refresh_recent_files()

    def _clear_history(self) -> None:
        RecentFilesManager.clear_recent_files()
        self.refresh_recent_files()
