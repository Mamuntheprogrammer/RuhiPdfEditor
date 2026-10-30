"""
Main PDF engine wrapping PyMuPDF.

Provides document open / save / close, per-page rendering, text
extraction, and the logic that "burns" annotations into the PDF
at save time.
"""

from __future__ import annotations

import logging
import math
import os
import stat
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz
sys.modules.setdefault("fitz", fitz)
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
    """Represents an existing text block found in the PDF with auto-detected font features."""
    page_index: int
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1
    text: str
    font_name: str
    font_size: float
    bold: bool = False
    italic: bool = False
    color: str = "#000000"


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
    def is_open(self) -> bool:
        """Return True if a document is currently open."""
        return self._doc is not None

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

            # Ensure writable attributes on Windows if target file already exists
            if target_path.exists():
                try:
                    os.chmod(target_path, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass

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
        """Extract text blocks or individual words from a page with auto-detected font properties.

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

        # Extract spans with full font metadata from page dictionary
        spans: list[dict] = []
        try:
            page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue  # skip image blocks
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            spans.append(span)
        except Exception:
            logger.exception("get_text('dict') failed on page %d", page_index)

        def _parse_span(span_dict: dict) -> tuple[str, float, bool, bool, str]:
            font_raw = span_dict.get("font", "")
            flags = int(span_dict.get("flags", 0))
            size = float(span_dict.get("size", 12.0))
            color_int = int(span_dict.get("color", 0))

            # Detect bold & italic from flags and font name
            is_bold = bool(flags & 16) or ("bold" in font_raw.lower()) or ("black" in font_raw.lower())
            is_italic = bool(flags & 2) or ("italic" in font_raw.lower()) or ("oblique" in font_raw.lower())

            # Clean font family name: strip subset prefix (e.g. ABCDEF+)
            clean_name = font_raw
            if "+" in clean_name:
                parts = clean_name.split("+", 1)
                if len(parts[0]) == 6:
                    clean_name = parts[1]

            # Strip standard font style suffixes
            for suffix in ("-BoldItalic", "-BoldOblique", "-Bold", "-Italic", "-Oblique", "-Regular", ",Bold", ",Italic", "MT", "PS"):
                if clean_name.endswith(suffix):
                    clean_name = clean_name[:-len(suffix)]

            # Map standard PDF font families to clean desktop names
            fn_lower = clean_name.lower()
            if "helv" in fn_lower or "arial" in fn_lower:
                clean_name = "Arial"
            elif "times" in fn_lower:
                clean_name = "Times New Roman"
            elif "courier" in fn_lower:
                clean_name = "Courier New"
            elif "calibri" in fn_lower:
                clean_name = "Calibri"
            elif "segoe" in fn_lower:
                clean_name = "Segoe UI"
            elif "tahoma" in fn_lower:
                clean_name = "Tahoma"

            # Convert integer color to hex "#RRGGBB"
            r = (color_int >> 16) & 0xFF
            g = (color_int >> 8) & 0xFF
            b = color_int & 0xFF
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            return clean_name, size, is_bold, is_italic, hex_color

        if level == "word":
            try:
                words = page.get_text("words")
                dict_blocks = page_dict.get("blocks", [])
                raw_extracted: list[dict] = []
                for w in words:
                    x0, y0, x1, y1, word_text = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
                    if not word_text.strip():
                        continue

                    cx = (x0 + x1) / 2.0
                    cy = (y0 + y1) / 2.0
                    matched_span = None

                    # 1. Primary lookup: directly index into page_dict using PyMuPDF block & line indices
                    try:
                        b_idx = int(w[5])
                        l_idx = int(w[6])
                        if b_idx < len(dict_blocks):
                            lines = dict_blocks[b_idx].get("lines", [])
                            if l_idx < len(lines):
                                line_spans = lines[l_idx].get("spans", [])
                                if len(line_spans) == 1:
                                    matched_span = line_spans[0]
                                else:
                                    for s in line_spans:
                                        sb = s.get("bbox", (0, 0, 0, 0))
                                        if (sb[0] - 2.0) <= cx <= (sb[2] + 2.0):
                                            matched_span = s
                                            break
                                    if not matched_span and line_spans:
                                        matched_span = line_spans[0]
                    except (IndexError, KeyError, TypeError, ValueError):
                        pass

                    # 2. Secondary fallback: search across all spans on page
                    if matched_span is None:
                        for s in spans:
                            sb = s.get("bbox", (0, 0, 0, 0))
                            if (sb[0] - 4.0) <= cx <= (sb[2] + 4.0) and (min(sb[1], y0) <= max(sb[3], y1)):
                                matched_span = s
                                break

                    if matched_span:
                        fn, sz, bld, itl, col = _parse_span(matched_span)
                    else:
                        fn, sz, bld, itl, col = ("Arial", max(8.0, y1 - y0), False, False, "#000000")

                    raw_extracted.append({
                        "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                        "text": word_text,
                        "fn": fn, "sz": sz, "bld": bld, "itl": itl, "col": col,
                    })

                # Merge adjacent and overlapping word fragments on the same line (crucial for complex Indic/Bangla vowels and ligatures)
                merged_items: list[dict] = []
                for item in raw_extracted:
                    if not merged_items:
                        merged_items.append(item)
                        continue

                    prev = merged_items[-1]
                    # Check if items are on the same line
                    h_a = item["y1"] - item["y0"]
                    h_b = prev["y1"] - prev["y0"]
                    same_line = abs(item["y0"] - prev["y0"]) <= max(6.0, max(h_a, h_b) * 0.5)

                    # Check if horizontally overlapping or touching without space gap
                    overlap = (item["x0"] <= prev["x1"] + 1.5) and (prev["x0"] <= item["x1"] + 1.5)
                    has_bangla = any(0x0980 <= ord(c) <= 0x09FF for c in (prev["text"] + item["text"]))

                    if same_line and (overlap or (has_bangla and item["x0"] <= prev["x1"] + 2.5)):
                        # Combine bounding box and text
                        prev["x0"] = min(prev["x0"], item["x0"])
                        prev["y0"] = min(prev["y0"], item["y0"])
                        prev["x1"] = max(prev["x1"], item["x1"])
                        prev["y1"] = max(prev["y1"], item["y1"])
                        prev["text"] = unicodedata.normalize("NFC", prev["text"] + item["text"])
                        if prev["fn"] == "Arial" and item["fn"] != "Arial":
                            prev["fn"] = item["fn"]
                        if item["sz"] > prev["sz"]:
                            prev["sz"] = item["sz"]
                    else:
                        merged_items.append(item)

                for m in merged_items:
                    blocks.append(
                        TextBlock(
                            page_index=page_index,
                            rect=(m["x0"], m["y0"], m["x1"], m["y1"]),
                            text=unicodedata.normalize("NFC", m["text"]),
                            font_name=m["fn"],
                            font_size=m["sz"],
                            bold=m["bld"],
                            italic=m["itl"],
                            color=m["col"],
                        )
                    )
            except Exception:
                logger.exception("get_text('words') failed on page %d", page_index)

        # Fallback to spans if words was empty or level == "span"
        if not blocks:
            for s in spans:
                bbox = s.get("bbox", (0, 0, 0, 0))
                text = s.get("text", "")
                if not text.strip():
                    continue
                fn, sz, bld, itl, col = _parse_span(s)
                blocks.append(
                    TextBlock(
                        page_index=page_index,
                        rect=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                        text=text,
                        font_name=fn,
                        font_size=sz,
                        bold=bld,
                        italic=itl,
                        color=col,
                    )
                )

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
                    underline=getattr(tb, "underline", False),
                    strikethrough=getattr(tb, "strikethrough", False),
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
                    opacity = getattr(img, "opacity", 1.0)
                    if opacity is not None and opacity < 0.999:
                        img_bytes = _apply_image_opacity(img.image_path, opacity)
                        if img_bytes:
                            page.insert_image(r, stream=img_bytes, overlay=True)
                        else:
                            page.insert_image(r, filename=img.image_path, overlay=True)
                    else:
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
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        strikethrough: bool = False,
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
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    strikethrough=strikethrough,
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


def _apply_image_opacity(image_path: str, opacity: float) -> bytes:
    """Return PNG bytes of the image with the specified opacity applied to its alpha channel."""
    # Attempt with PIL first
    try:
        from PIL import Image
        import io
        with Image.open(image_path) as im:
            rgba = im.convert("RGBA")
            r, g, b, a = rgba.split()
            op_clamped = max(0.0, min(1.0, float(opacity)))
            a = a.point(lambda p: int(round(p * op_clamped)))
            rgba.putalpha(a)
            buf = io.BytesIO()
            rgba.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        pass

    # Fallback with QImage / PySide6
    try:
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtCore import QBuffer, QIODevice, Qt
        src = QImage(image_path)
        if not src.isNull():
            out = QImage(src.size(), QImage.Format.Format_ARGB32_Premultiplied)
            out.fill(Qt.GlobalColor.transparent)
            painter = QPainter(out)
            painter.setOpacity(max(0.0, min(1.0, float(opacity))))
            painter.drawImage(0, 0, src)
            painter.end()
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            out.save(buf, "PNG")
            return bytes(buf.data())
    except Exception:
        pass

    return b""
