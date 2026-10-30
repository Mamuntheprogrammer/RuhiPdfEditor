"""
Page-level manipulation utilities with undoable commands.

Provides static helpers for common page operations (delete, rotate,
reorder, merge, split, insert blank) and matching :class:`Command`
subclasses that integrate with the :class:`UndoStack`.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from core.undo_redo import Command

logger = logging.getLogger(__name__)


# ===================================================================
# Static helpers
# ===================================================================

class PageTools:
    """Utilities for page-level operations on PDF documents."""

    @staticmethod
    def delete_page(doc: fitz.Document, page_index: int) -> None:
        """Delete the page at *page_index* from *doc*.

        Raises ``IndexError`` if the index is out of range.
        """
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Page index {page_index} out of range (0..{len(doc) - 1})")
        doc.delete_page(page_index)
        logger.debug("Deleted page %d", page_index)

    @staticmethod
    def rotate_page(doc: fitz.Document, page_index: int, angle: int = 90) -> None:
        """Rotate the page at *page_index* by *angle* degrees (90, 180, 270).

        The rotation is cumulative with any existing page rotation.
        """
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Page index {page_index} out of range")
        if angle not in (90, 180, 270):
            raise ValueError(f"Angle must be 90, 180, or 270 – got {angle}")
        page = doc[page_index]
        new_rotation = (page.rotation + angle) % 360
        page.set_rotation(new_rotation)
        logger.debug("Rotated page %d by %d° → now %d°", page_index, angle, new_rotation)

    @staticmethod
    def reorder_pages(doc: fitz.Document, new_order: list[int]) -> None:
        """Reorder pages according to *new_order*.

        *new_order* is a list of current page indices in the desired
        new order.  ``doc.select(new_order)`` removes any pages whose
        indices do not appear.
        """
        if not new_order:
            raise ValueError("new_order must not be empty")
        doc.select(new_order)
        logger.debug("Reordered pages: %s", new_order)

    @staticmethod
    def merge_pdfs(paths: list[str], output_path: str) -> None:
        """Merge multiple PDF files into a single output file.

        Pages are appended in the order the *paths* list provides.
        """
        if not paths:
            raise ValueError("paths list must not be empty")

        merged = fitz.open()
        try:
            for p in paths:
                src_path = Path(p).resolve()
                if not src_path.exists():
                    raise FileNotFoundError(f"PDF not found: {src_path}")
                src = fitz.open(str(src_path))
                merged.insert_pdf(src)
                src.close()

            out = Path(output_path).resolve()
            merged.save(str(out), garbage=4, deflate=True)
            logger.info("Merged %d files → %s", len(paths), out)
        finally:
            merged.close()

    @staticmethod
    def split_pdf(
        doc: fitz.Document,
        ranges: list[tuple[int, int]],
        output_dir: str,
    ) -> list[str]:
        """Split *doc* into multiple files by page ranges.

        Each range is ``(start_page, end_page)`` **inclusive**.
        Returns the list of created file paths.
        """
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        created: list[str] = []

        for idx, (start, end) in enumerate(ranges, start=1):
            part = fitz.open()
            try:
                part.insert_pdf(doc, from_page=start, to_page=end)
                out_file = out_dir / f"part_{idx}_pages_{start + 1}-{end + 1}.pdf"
                part.save(str(out_file), garbage=4, deflate=True)
                created.append(str(out_file))
                logger.debug("Split part %d → %s", idx, out_file)
            finally:
                part.close()

        return created

    @staticmethod
    def insert_blank_page(
        doc: fitz.Document,
        page_index: int,
        width: float = 595.0,
        height: float = 842.0,
    ) -> None:
        """Insert a blank page at *page_index* (A4 by default).

        ``pno=-1`` or ``pno >= len(doc)`` appends at the end.
        """
        doc.new_page(pno=page_index, width=width, height=height)
        logger.debug(
            "Inserted blank page at index %d (%.0f×%.0f)", page_index, width, height
        )


# ===================================================================
# Undoable commands
# ===================================================================

class DeletePageCommand(Command):
    """Undoable page deletion.

    On ``execute`` the page content is extracted to a temporary
    single-page document so it can be re-inserted on ``undo``.
    """

    def __init__(self, doc: fitz.Document, page_index: int) -> None:
        self._doc = doc
        self._page_index = page_index
        # Backup document holding the deleted page
        self._backup: fitz.Document | None = None

    def execute(self) -> None:
        """Delete the page after backing it up."""
        if self._page_index < 0 or self._page_index >= len(self._doc):
            raise IndexError(f"Page index {self._page_index} out of range")

        # Save page into a temporary in-memory doc
        self._backup = fitz.open()
        self._backup.insert_pdf(
            self._doc,
            from_page=self._page_index,
            to_page=self._page_index,
        )
        self._doc.delete_page(self._page_index)
        logger.debug("DeletePageCommand: deleted page %d", self._page_index)

    def undo(self) -> None:
        """Re-insert the deleted page at its original position."""
        if self._backup is None:
            logger.warning("DeletePageCommand.undo: no backup available")
            return

        # Clamp the insert position in case the document shrank further
        insert_at = min(self._page_index, len(self._doc))
        # insert_pdf inserts *after* pno, but we need *at* pno.
        # We insert after (insert_at - 1) which places the page at insert_at.
        if insert_at == 0:
            # No page before index 0; insert at the start by inserting
            # at pno=-1 (beginning) — but fitz uses pno as "insert after",
            # so we insert, then move.
            self._doc.insert_pdf(self._backup, from_page=0, to_page=0, start_at=0)
        else:
            self._doc.insert_pdf(
                self._backup, from_page=0, to_page=0, start_at=insert_at
            )
        logger.debug("DeletePageCommand: restored page at %d", insert_at)

    @property
    def description(self) -> str:
        return f"Delete page {self._page_index + 1}"


class RotatePageCommand(Command):
    """Undoable page rotation.

    Stores the original rotation so ``undo`` can restore it exactly.
    """

    def __init__(self, doc: fitz.Document, page_index: int, angle: int = 90) -> None:
        self._doc = doc
        self._page_index = page_index
        self._angle = angle
        self._old_rotation: int = 0

    def execute(self) -> None:
        page = self._doc[self._page_index]
        self._old_rotation = page.rotation
        new_rotation = (self._old_rotation + self._angle) % 360
        page.set_rotation(new_rotation)
        logger.debug(
            "RotatePageCommand: page %d  %d° → %d°",
            self._page_index, self._old_rotation, new_rotation,
        )

    def undo(self) -> None:
        page = self._doc[self._page_index]
        page.set_rotation(self._old_rotation)
        logger.debug(
            "RotatePageCommand.undo: page %d → %d°",
            self._page_index, self._old_rotation,
        )

    @property
    def description(self) -> str:
        return f"Rotate page {self._page_index + 1} by {self._angle}°"


class ReorderPagesCommand(Command):
    """Undoable page reorder.

    Because ``doc.select()`` is destructive (pages not in the list are
    removed), this command saves the full document bytes before
    reordering so that ``undo`` can restore the original state.
    """

    def __init__(self, doc: fitz.Document, new_order: list[int]) -> None:
        self._doc = doc
        self._new_order = list(new_order)
        # Snapshot of the entire document before reordering
        self._snapshot_bytes: bytes = b""

    def execute(self) -> None:
        # Take a snapshot *before* mutating
        self._snapshot_bytes = self._doc.tobytes(garbage=0, deflate=False)
        self._doc.select(self._new_order)
        logger.debug("ReorderPagesCommand: reordered to %s", self._new_order)

    def undo(self) -> None:
        if not self._snapshot_bytes:
            logger.warning("ReorderPagesCommand.undo: no snapshot available")
            return

        # Restore from snapshot.  We cannot re-open self._doc in-place,
        # so we clear it and re-insert all pages from the snapshot.
        restored = fitz.open("pdf", self._snapshot_bytes)

        # Remove all current pages
        while len(self._doc) > 0:
            self._doc.delete_page(0)

        # Re-insert every page from the snapshot
        self._doc.insert_pdf(restored)
        restored.close()
        logger.debug("ReorderPagesCommand.undo: restored original page order")

    @property
    def description(self) -> str:
        return "Reorder pages"


class InsertBlankPageCommand(Command):
    """Undoable blank page insertion."""

    def __init__(
        self,
        doc: fitz.Document,
        page_index: int,
        width: float = 595.0,
        height: float = 842.0,
    ) -> None:
        self._doc = doc
        self._page_index = page_index
        self._width = width
        self._height = height

    def execute(self) -> None:
        self._doc.new_page(pno=self._page_index, width=self._width, height=self._height)
        logger.debug("InsertBlankPageCommand: inserted at %d", self._page_index)

    def undo(self) -> None:
        # The inserted page sits at self._page_index (or end if clamped)
        actual_index = min(self._page_index, len(self._doc) - 1)
        self._doc.delete_page(actual_index)
        logger.debug("InsertBlankPageCommand.undo: removed page %d", actual_index)

    @property
    def description(self) -> str:
        return f"Insert blank page at {self._page_index + 1}"
