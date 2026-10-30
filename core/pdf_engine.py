"""
Main PDF engine wrapping PyMuPDF.

Provides document open / save / close, per-page rendering, text
extraction, and the logic that "burns" annotations into the PDF
at save time.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap

from core.annotations import (
    AnnotationManager,
    FreehandData,
    HighlightData,
    ImageData,
    ShapeData,
    TextBoxData,
)
from core.text_renderer import TextRenderer

logger = logging.getLogger(__name__)


# ===================================================================
# Helper data class for extracted text
# ===================================================================

@dataclass
class TextBlock:
    """Represents an existing text block found in the PDF."""
    page_index: int
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1
    text: str
    font_name: str
    font_size: float


# ===================================================================
# PDF Engine
# ===================================================================

class PdfEngine(QObject):
    """High-level wrapper around a ``fitz.Document``.

    Emits Qt signals so that the UI can stay in sync with the
    document's state.
    """

    document_changed = Signal()
    page_count_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._doc: fitz.Document | None = None
        self._file_path: str | None = None
        self._text_renderer = TextRenderer()
        self._annotation_mgr = AnnotationManager()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def document(self) -> fitz.Document | None:
        """The currently open ``fitz.Document``, or *None*."""
        return self._doc

    @property
    def file_path(self) -> str | None:
        """Path of the currently open file, or *None* for unsaved docs."""
        return self._file_path

    @property
    def page_count(self) -> int:
        """Number of pages (0 when no document is open)."""
        if self._doc is None:
            return 0
        return len(self._doc)

    @property
    def text_renderer(self) -> TextRenderer:
        """The shared :class:`TextRenderer` instance."""
        return self._text_renderer

    @property
    def annotation_manager(self) -> AnnotationManager:
        """The shared :class:`AnnotationManager` instance."""
        return self._annotation_mgr

    # ------------------------------------------------------------------
    # Document lifecycle
    # ------------------------------------------------------------------

    def open(self, path: str) -> None:
        """Open a PDF file from *path*.

        Loads the file bytes into memory to prevent OS file locks on Windows,
        allowing direct in-place saves and edits without permission errors.

        Raises ``FileNotFoundError`` if the file does not exist, or
        ``RuntimeError`` if PyMuPDF cannot parse it.
        """
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            with open(resolved, "rb") as f:
                file_bytes = f.read()
            self._doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            logger.exception("Failed to open '%s'", resolved)
            raise RuntimeError(f"Cannot open PDF: {exc}") from exc

        self._file_path = str(resolved)
        self._annotation_mgr.clear()
        logger.info("Opened PDF: %s (%d pages)", resolved, len(self._doc))
        self.document_changed.emit()
        self.page_count_changed.emit(self.page_count)

    def create_new(self) -> None:
        """Create a new, empty PDF document with one blank A4 page."""
        self.close()
        self._doc = fitz.open()  # new empty document
        self._doc.new_page(width=595, height=842)  # A4 in points
        self._file_path = None
        self._annotation_mgr.clear()
        logger.info("Created new empty PDF.")
        self.document_changed.emit()
        self.page_count_changed.emit(self.page_count)

    def save(self, path: str | None = None) -> None:
        """Save the document, burning annotations into the exported file.

        The live working document in memory retains its annotations in the manager
        so they remain editable multiple times without duplicate burn-in.

        Parameters
        ----------
        path:
            Destination path. When *None* the document is saved back
            to its original location.
        """
        if self._doc is None:
            raise RuntimeError("No document is open.")

        target = path or self._file_path
        if target is None:
            raise RuntimeError("No file path specified and document has never been saved.")

        try:
            target_path = Path(target).resolve()

            # Burn annotations into an exported document so self._doc remains cleanly editable
            doc_bytes = self._doc.tobytes(garbage=0, deflate=True)
            export_doc = fitz.open(stream=doc_bytes, filetype="pdf")
            try:
                self.apply_annotations(export_doc)
                saved_bytes = export_doc.tobytes(garbage=4, deflate=True)
            finally:
                export_doc.close()

            # Write bytes directly using Python's open() to avoid Windows file-lock permission errors
            with open(target_path, "wb") as f:
                f.write(saved_bytes)

            self._file_path = str(target_path)
            logger.info("Saved with annotations burned into %s", target_path)
            self.document_changed.emit()
        except Exception:
            logger.exception("Save failed")
            raise

    def save_as(self, path: str) -> None:
        """Save to a new path (always burns annotations into the exported file)."""
        self.save(path)

    def close(self) -> None:
        """Close the current document and free resources."""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                logger.debug("Error closing document (ignored).")
            self._doc = None
        self._file_path = None
        self._annotation_mgr.clear()
        self.document_changed.emit()
        self.page_count_changed.emit(0)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_page(self, page_index: int, zoom: float = 1.0) -> QPixmap:
        """Render a page to a ``QPixmap`` at the given *zoom* level.

        Raises ``IndexError`` if *page_index* is out of range.
        """
        self._require_doc()
        if page_index < 0 or page_index >= self.page_count:
            raise IndexError(f"Page index {page_index} out of range (0..{self.page_count - 1})")

        page: fitz.Page = self._doc[page_index]  # type: ignore[index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return self._fitz_pixmap_to_qpixmap(pix)

    def render_thumbnail(self, page_index: int, max_size: int = 200) -> QPixmap:
        """Render a thumbnail-sized preview of a page.

        The longest dimension will be at most *max_size* pixels.
        """
        self._require_doc()
        if page_index < 0 or page_index >= self.page_count:
            raise IndexError(f"Page index {page_index} out of range")

        page: fitz.Page = self._doc[page_index]  # type: ignore[index]
        pw, ph = page.rect.width, page.rect.height
        scale = max_size / max(pw, ph)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return self._fitz_pixmap_to_qpixmap(pix)

    def export_page_as_image(
        self, page_index: int, output_path: str, dpi: int = 300
    ) -> None:
        """Export a single page as a PNG/JPG image at *dpi* resolution."""
        self._require_doc()
        if page_index < 0 or page_index >= self.page_count:
            raise IndexError(f"Page index {page_index} out of range")

        page: fitz.Page = self._doc[page_index]  # type: ignore[index]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        out = Path(output_path).resolve()
        extension = out.suffix.lower()
        if extension in (".jpg", ".jpeg"):
            pix.save(str(out), output="jpeg")
        else:
            pix.save(str(out))  # default PNG
        logger.info("Exported page %d → %s at %d dpi", page_index, out, dpi)

    # ------------------------------------------------------------------
    # Page information / text extraction
    # ------------------------------------------------------------------

    def get_page_size(self, page_index: int) -> tuple[float, float]:
        """Return ``(width, height)`` of the page in PDF points."""
        self._require_doc()
        page: fitz.Page = self._doc[page_index]  # type: ignore[index]
        return (page.rect.width, page.rect.height)

    def get_text_blocks(self, page_index: int, level: str = "word") -> list[TextBlock]:
        """Extract text blocks or individual words from a page.

        Parameters
        ----------
        page_index : int
            Page index to inspect.
        level : str
            ``"word"`` for single-word granularity (default, enabling word-level erasing),
            or ``"span"`` for line/span-level granularity.
        """
        self._require_doc()
        page: fitz.Page = self._doc[page_index]  # type: ignore[index]
        blocks: list[TextBlock] = []

        if level == "word":
            try:
                words = page.get_text("words")
                for w in words:
                    x0, y0, x1, y1, word_text = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
                    if not word_text.strip():
                        continue
                    blocks.append(
                        TextBlock(
                            page_index=page_index,
                            rect=(x0, y0, x1, y1),
                            text=word_text,
                            font_name="",
                            font_size=max(8.0, y1 - y0),
                        )
                    )
            except Exception:
                logger.exception("get_text('words') failed on page %d", page_index)

        # Fallback to spans if words was empty or level == "span"
        if not blocks:
            try:
                page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
                for block in page_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue  # skip image blocks
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            text = span.get("text", "")
                            if not text.strip():
                                continue
                            blocks.append(
                                TextBlock(
                                    page_index=page_index,
                                    rect=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                                    text=text,
                                    font_name=span.get("font", ""),
                                    font_size=float(span.get("size", 0.0)),
                                )
                            )
            except Exception:
                logger.exception("get_text('dict') failed on page %d", page_index)

        return blocks

    # ------------------------------------------------------------------
    # Annotations → PDF burn-in
    # ------------------------------------------------------------------

    def apply_annotations(self, doc: fitz.Document) -> None:
        """Burn all annotations from the :class:`AnnotationManager` into *doc*.

        After saving, the annotations remain in the manager so they
        can still be edited (or re-applied on the next save).
        """
        for page_index in range(len(doc)):
            page: fitz.Page = doc[page_index]
            annots = self._annotation_mgr.get_annotations_for_page(page_index)

            # ---- Text boxes ----
            for tb in annots["text_boxes"]:
                tb: TextBoxData
                self._text_renderer.insert_text_to_page(
                    page,
                    rect=tb.rect,
                    text=tb.text,
                    font_family=tb.font_family,
                    font_size=tb.font_size,
                    color=tb.color,
                    bold=tb.bold,
                    italic=tb.italic,
                )

            # ---- Highlights / underlines / strikethroughs ----
            for hl in annots["highlights"]:
                hl: HighlightData
                quad = fitz.Rect(*hl.rect)
                try:
                    if hl.annotation_type == "highlight":
                        annot = page.add_highlight_annot(quad)
                    elif hl.annotation_type == "underline":
                        annot = page.add_underline_annot(quad)
                    elif hl.annotation_type == "strikethrough":
                        annot = page.add_strikeout_annot(quad)
                    else:
                        continue
                    # Set colour from hex
                    r, g, b = _hex_to_rgb(hl.color)
                    annot.set_colors(stroke=(r, g, b))
                    annot.set_opacity(hl.opacity)
                    annot.update()
                except Exception:
                    logger.exception("Failed to add highlight on page %d", page_index)

            # ---- Shapes ----
            for sh in annots["shapes"]:
                sh: ShapeData
                try:
                    shape = page.new_shape()
                    stroke_rgb = _hex_to_rgb(sh.stroke_color)
                    fill_rgb = _hex_to_rgb(sh.fill_color) if sh.fill_color else None

                    if sh.shape_type == "rect":
                        r = fitz.Rect(
                            sh.start_point[0], sh.start_point[1],
                            sh.end_point[0], sh.end_point[1],
                        )
                        shape.draw_rect(r)
                    elif sh.shape_type == "line":
                        p1 = fitz.Point(sh.start_point[0], sh.start_point[1])
                        p2 = fitz.Point(sh.end_point[0], sh.end_point[1])
                        shape.draw_line(p1, p2)
                    elif sh.shape_type == "arrow":
                        p1 = fitz.Point(sh.start_point[0], sh.start_point[1])
                        p2 = fitz.Point(sh.end_point[0], sh.end_point[1])
                        shape.draw_line(p1, p2)
                        # Draw arrowhead
                        _draw_arrowhead(shape, p1, p2, size=10.0)

                    shape.finish(
                        color=stroke_rgb,
                        fill=fill_rgb,
                        width=sh.stroke_width,
                    )
                    shape.commit()
                except Exception:
                    logger.exception("Failed to draw shape on page %d", page_index)

            # ---- Freehands ----
            for fh in annots["freehands"]:
                fh: FreehandData
                if len(fh.points) < 2:
                    continue
                try:
                    shape = page.new_shape()
                    points = [fitz.Point(x, y) for x, y in fh.points]
                    shape.draw_polyline(points)
                    rgb = _hex_to_rgb(fh.color)
                    shape.finish(color=rgb, width=fh.width, closePath=False)
                    shape.commit()
                except Exception:
                    logger.exception("Failed to draw freehand on page %d", page_index)

            # ---- Images ----
            for img in annots["images"]:
                img: ImageData
                if not img.image_path or not Path(img.image_path).exists():
                    logger.warning("Image file missing: %s", img.image_path)
                    continue
                try:
                    r = fitz.Rect(*img.rect)
                    page.insert_image(r, filename=img.image_path, overlay=True)
                except Exception:
                    logger.exception("Failed to insert image on page %d", page_index)

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    def redact_area(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        replacement_text: str = "",
        font_family: str = "Noto Sans Bengali",
        font_size: float = 12.0,
        color: str = "#000000",
    ) -> None:
        """White-out an area and optionally place replacement text.

        Uses PyMuPDF's redaction workflow: add a redaction annotation,
        apply it (which removes content under the rect), then optionally
        insert new text with :meth:`TextRenderer.insert_text_to_page`.
        """
        self._require_doc()
        page: fitz.Page = self._doc[page_index]  # type: ignore[index]

        try:
            annot = page.add_redact_annot(fitz.Rect(*rect))
            annot.update()
            page.apply_redactions()
            logger.debug("Redacted area %s on page %d", rect, page_index)

            if replacement_text:
                self._text_renderer.insert_text_to_page(
                    page,
                    rect=rect,
                    text=replacement_text,
                    font_family=font_family,
                    font_size=font_size,
                    color=color,
                )
        except Exception:
            logger.exception("Redaction failed on page %d", page_index)
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_doc(self) -> None:
        """Raise if no document is open."""
        if self._doc is None:
            raise RuntimeError("No document is open.")

    @staticmethod
    def _fitz_pixmap_to_qpixmap(pix: fitz.Pixmap) -> QPixmap:
        """Convert a ``fitz.Pixmap`` to a ``QPixmap``.

        Handles both RGB and RGBA pixmaps.
        """
        if pix.alpha:
            fmt = QImage.Format.Format_RGBA8888
            samples = pix.samples
        else:
            fmt = QImage.Format.Format_RGB888
            samples = pix.samples

        qimg = QImage(samples, pix.width, pix.height, pix.stride, fmt)
        # QImage does not own the data buffer, so we must copy before
        # the fitz.Pixmap (and its samples) is garbage-collected.
        qimg = qimg.copy()
        return QPixmap.fromImage(qimg)


# ===================================================================
# Module-level utilities
# ===================================================================

def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert ``#RRGGBB`` to an ``(r, g, b)`` tuple with values 0-1."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.0, 0.0, 0.0)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r / 255.0, g / 255.0, b / 255.0)


def _draw_arrowhead(
    shape: fitz.Shape,
    p1: fitz.Point,
    p2: fitz.Point,
    size: float = 10.0,
) -> None:
    """Draw a simple triangular arrowhead at *p2* pointing away from *p1*."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.hypot(dx, dy)
    if length == 0:
        return

    # Unit vector along the line
    ux, uy = dx / length, dy / length
    # Perpendicular
    px, py = -uy, ux

    # Two base points of the triangle
    base_x = p2.x - ux * size
    base_y = p2.y - uy * size

    left = fitz.Point(base_x + px * size * 0.4, base_y + py * size * 0.4)
    right = fitz.Point(base_x - px * size * 0.4, base_y - py * size * 0.4)

    shape.draw_polyline([left, p2, right])
