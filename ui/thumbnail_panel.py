"""
Left sidebar showing page thumbnails for the PDF Editor.

Provides a :class:`ThumbnailPanel` dock widget with drag-to-reorder support,
page-number labels, and a right-click context menu for page operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, QSize, QMimeData
from PySide6.QtGui import QPixmap, QIcon, QDrag
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QWidget,
)

if TYPE_CHECKING:
    from core.pdf_engine import PdfEngine
    from ui.i18n import I18n


class ThumbnailPanel(QDockWidget):
    """Left sidebar showing page thumbnails with drag-to-reorder.

    Features:
    * Icon-mode list with large thumbnails rendered via PdfEngine.
    * Internal drag-and-drop for page reordering.
    * Right-click context menu: Delete, Rotate, Insert Blank.
    """

    # ---- Signals ---- #
    page_selected = Signal(int)           # page index
    page_reordered = Signal(list)         # new order as list of old indices
    page_delete_requested = Signal(int)
    page_rotate_requested = Signal(int)
    page_insert_requested = Signal(int)   # insert blank *after* this index

    # Maximum thumbnail width/height in pixels.
    THUMB_SIZE: int = 160

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self._i18n = i18n
        self.setObjectName("ThumbnailPanel")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(self.THUMB_SIZE, self.THUMB_SIZE))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setWrapping(False)
        self._list.setFlow(QListWidget.Flow.TopToBottom)
        self._list.setSpacing(8)
        self._list.setMovement(QListWidget.Movement.Snap)
        self._list.setUniformItemSizes(False)

        # Drag-and-drop for internal reordering
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Right-click context menu
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)

        # Selection change → page_selected
        self._list.currentRowChanged.connect(self._on_current_row_changed)

        # Detect reorder via internal model changes
        self._list.model().rowsMoved.connect(self._on_rows_moved)

        self.setWidget(self._list)

        # Track original page indices to emit correct reorder signal
        self._page_indices: list[int] = []

        self.update_translations(i18n)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def refresh(self, engine: PdfEngine) -> None:
        """Reload all thumbnails from the engine.

        Args:
            engine: The PDF engine to render thumbnails from.
        """
        self._list.blockSignals(True)
        self._list.clear()
        self._page_indices.clear()

        count: int = engine.page_count
        for idx in range(count):
            pixmap: QPixmap = engine.render_thumbnail(idx, max_size=self.THUMB_SIZE)
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            label = f"{self._i18n.t('page')} {idx + 1}"
            item.setText(label)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setSizeHint(QSize(self.THUMB_SIZE + 20, self.THUMB_SIZE + 30))
            self._list.addItem(item)
            self._page_indices.append(idx)

        if count > 0:
            self._list.setCurrentRow(0)
        self._list.blockSignals(False)

    def update_thumbnail(self, page_index: int, engine: PdfEngine) -> None:
        """Update a single thumbnail after a page has been modified.

        Args:
            page_index: Index of the page to re-render.
            engine: The PDF engine.
        """
        row = self._row_for_page(page_index)
        if row is None:
            return
        item = self._list.item(row)
        if item is None:
            return
        pixmap = engine.render_thumbnail(page_index, max_size=self.THUMB_SIZE)
        item.setIcon(QIcon(pixmap))

    def set_current_page(self, page_index: int) -> None:
        """Highlight the current page in the list.

        Args:
            page_index: The zero-based page index to select.
        """
        row = self._row_for_page(page_index)
        if row is not None:
            self._list.blockSignals(True)
            self._list.setCurrentRow(row)
            self._list.blockSignals(False)

    def update_translations(self, i18n: I18n) -> None:
        """Refresh strings after a language change.

        Args:
            i18n: The new internationalisation helper.
        """
        self._i18n = i18n
        self.setWindowTitle(i18n.t("pages"))

        # Update item labels
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None:
                page_idx = item.data(Qt.ItemDataRole.UserRole)
                item.setText(f"{i18n.t('page')} {page_idx + 1}")

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _row_for_page(self, page_index: int) -> int | None:
        """Return the list row corresponding to *page_index*, or ``None``."""
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == page_index:
                return row
        return None

    def _on_current_row_changed(self, row: int) -> None:
        """Emit :pyattr:`page_selected` when the user clicks a thumbnail."""
        if row < 0:
            return
        item = self._list.item(row)
        if item is not None:
            page_idx: int = item.data(Qt.ItemDataRole.UserRole)
            self.page_selected.emit(page_idx)

    def _on_rows_moved(self) -> None:
        """Emit :pyattr:`page_reordered` after a drag-and-drop reorder."""
        new_order: list[int] = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item is not None:
                new_order.append(item.data(Qt.ItemDataRole.UserRole))
        if new_order != self._page_indices:
            self._page_indices = list(new_order)
            self.page_reordered.emit(new_order)

    def _show_context_menu(self, position) -> None:  # type: ignore[override]
        """Show right-click context menu for page operations."""
        item = self._list.itemAt(position)
        if item is None:
            return
        page_idx: int = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        delete_action = menu.addAction(self._i18n.t("delete_page"))
        rotate_action = menu.addAction(self._i18n.t("rotate_page"))
        menu.addSeparator()
        insert_action = menu.addAction(self._i18n.t("insert_blank_page"))

        chosen = menu.exec(self._list.mapToGlobal(position))
        if chosen is delete_action:
            self.page_delete_requested.emit(page_idx)
        elif chosen is rotate_action:
            self.page_rotate_requested.emit(page_idx)
        elif chosen is insert_action:
            self.page_insert_requested.emit(page_idx)
