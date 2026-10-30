"""
Bangla-safe text rendering for PDF insertion and on-screen preview.

Uses PyMuPDF's ``insert_htmlbox`` (which delegates to the HarfBuzz
shaping pipeline) so that complex Bangla conjuncts, matras, and
reordering render correctly.  Qt's own HarfBuzz integration is used
for live preview pixmaps in the editor canvas.
"""

from __future__ import annotations

import html
import logging
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QPainter,
    QPixmap,
)

logger = logging.getLogger(__name__)


class TextRenderer:
    """Renders text with proper Bangla / complex-script shaping.

    Fonts are loaded from the bundled ``fonts/`` directory that sits
    next to the project root.  Each font is registered with *both*
    PyMuPDF (for PDF writing) and Qt (for on-screen preview).
    """

    # The fonts directory lives at <project_root>/fonts/ or sys._MEIPASS/fonts in frozen bundles
    FONT_DIR: Path = (
        Path(sys._MEIPASS) / "fonts"
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
        else Path(__file__).parent.parent / "fonts"
    )

    # Maps human-readable family names → variant → filename inside FONT_DIR.
    FONT_MAP: dict[str, dict[str, str]] = {
        "Noto Sans Bengali": {
            "regular": "NotoSansBengali-Regular.ttf",
            "bold": "NotoSansBengali-Bold.ttf",
        },
        "Kalpurush": {
            "regular": "Kalpurush.ttf",
        },
        "SolaimanLipi": {
            "regular": "SolaimanLipi.ttf",
        },
        "Noto Sans": {
            "regular": "NotoSans-Regular.ttf",
            "bold": "NotoSans-Bold.ttf",
            "italic": "NotoSans-Italic.ttf",
            "bold_italic": "NotoSans-BoldItalic.ttf",
        },
    }

    def __init__(self) -> None:
        # fitz.Font objects keyed by "<family>|<variant>"
        self._registered_fonts: dict[str, fitz.Font] = {}
        # Qt font-database IDs returned by addApplicationFont
        self._qt_font_ids: list[int] = []
        self._register_fonts()

    # ------------------------------------------------------------------
    # Font registration
    # ------------------------------------------------------------------

    def _register_fonts(self) -> None:
        """Register every font listed in :data:`FONT_MAP` with Qt and PyMuPDF."""
        from PySide6.QtGui import QGuiApplication

        has_qt_app = QGuiApplication.instance() is not None

        for family, variants in self.FONT_MAP.items():
            for variant, filename in variants.items():
                font_path = self.FONT_DIR / filename
                if not font_path.exists():
                    logger.warning("Font file not found – skipping: %s", font_path)
                    continue

                # ---- Qt registration (only if Qt application exists) ----
                if has_qt_app:
                    font_id = QFontDatabase.addApplicationFont(str(font_path))
                    if font_id == -1:
                        logger.warning("Qt failed to load font: %s", font_path)
                    else:
                        self._qt_font_ids.append(font_id)
                        logger.debug("Qt registered font %s (%s) id=%d", family, variant, font_id)

                # ---- PyMuPDF registration ----
                try:
                    fitz_font = fitz.Font(fontfile=str(font_path))
                    key = f"{family}|{variant}"
                    self._registered_fonts[key] = fitz_font
                    logger.debug("PyMuPDF registered font %s (%s)", family, variant)
                except Exception:
                    logger.exception("PyMuPDF failed to load font: %s", font_path)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_font_families(self) -> list[str]:
        """Return the list of available font family names."""
        return list(self.FONT_MAP.keys())

    # ------------------------------------------------------------------
    # PDF text insertion  (HarfBuzz via insert_htmlbox)
    # ------------------------------------------------------------------

    def insert_text_to_page(
        self,
        page: fitz.Page,
        rect: tuple[float, float, float, float],
        text: str,
        font_family: str = "Noto Sans Bengali",
        font_size: float = 14.0,
        color: str = "#000000",
        bold: bool = False,
        italic: bool = False,
    ) -> None:
        """Insert *text* into *page* using ``insert_htmlbox`` for proper shaping.

        An ``fitz.Archive`` is created so that ``@font-face`` CSS rules
        can reference the ``.ttf`` files by filename alone.

        Parameters
        ----------
        page:
            The ``fitz.Page`` to write on.
        rect:
            ``(x0, y0, x1, y1)`` rectangle in PDF points.
        text:
            The string to render (may contain Bangla / Unicode).
        font_family:
            One of the family names from :data:`FONT_MAP`.
        font_size:
            Size in points.
        color:
            CSS colour string, e.g. ``"#000000"``.
        bold:
            Whether to use the bold variant.
        italic:
            Whether to use the italic variant.
        """
        # Determine the variant key
        variant = _variant_key(bold, italic)

        # Resolve the family's available variants
        family_variants = self.FONT_MAP.get(font_family, {})

        # Fall back gracefully when the exact variant is unavailable
        chosen_filename = (
            family_variants.get(variant)
            or family_variants.get("regular")
        )
        if chosen_filename is None:
            logger.error("No font file found for family '%s'", font_family)
            return

        # Build @font-face CSS for every variant the family provides
        font_face_css = self._build_font_face_css(font_family)

        # Build the HTML snippet
        escaped_text = html.escape(text).replace("\n", "<br/>")
        font_weight = "bold" if bold else "normal"
        font_style = "italic" if italic else "normal"

        html_content = (
            f"<html><head><style>\n"
            f"{font_face_css}\n"
            f"* {{ margin: 0; padding: 0; }}\n"
            f"body {{ margin: 0; padding: 0; line-height: 1.25; }}\n"
            f"</style></head><body>\n"
            f"<div style=\"font-family: '{font_family}'; "
            f"font-size: {font_size}pt; "
            f"color: {color}; "
            f"font-weight: {font_weight}; "
            f"font-style: {font_style};\">"
            f"{escaped_text}"
            f"</div></body></html>"
        )

        # Create an archive pointing to the fonts directory so that
        # insert_htmlbox can locate the .ttf files referenced in CSS.
        try:
            archive = fitz.Archive(str(self.FONT_DIR))
            x0, y0, r2, r3 = rect
            num_lines = max(1, len(text.splitlines()))
            min_h = max(font_size * num_lines * 1.35 + 4.0, 10.0)
            min_w = max(font_size * 2.0, 20.0)

            if r2 <= x0 or r3 <= y0:
                target_rect = fitz.Rect(x0, y0, x0 + max(min_w, r2), y0 + max(min_h, r3))
            else:
                target_rect = fitz.Rect(x0, y0, max(r2, x0 + min_w), max(r3, y0 + min_h))
            target_rect.normalize()

            page.insert_htmlbox(target_rect, html_content, archive=archive)
            logger.debug(
                "Inserted text on page %d at %s (family=%s, size=%.1f)",
                page.number, rect, font_family, font_size,
            )
        except Exception:
            logger.exception("insert_htmlbox failed for page %d", page.number)

    # ------------------------------------------------------------------
    # Qt preview rendering
    # ------------------------------------------------------------------

    def ensure_qt_fonts_registered(self) -> None:
        """Register application fonts with Qt if an application is active and not yet registered."""
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            return
        if self._qt_font_ids:
            return
        for family, variants in self.FONT_MAP.items():
            for variant, filename in variants.items():
                font_path = self.FONT_DIR / filename
                if font_path.exists():
                    fid = QFontDatabase.addApplicationFont(str(font_path))
                    if fid != -1:
                        self._qt_font_ids.append(fid)

    def render_text_preview(
        self,
        text: str,
        font_family: str,
        font_size: float,
        color: str,
        bold: bool,
        italic: bool,
        width: int = 400,
        height: int = 100,
    ) -> QPixmap:
        """Render a text preview using Qt (HarfBuzz) for the editor canvas.

        Returns a ``QPixmap`` with the rendered text on a transparent
        background.
        """
        self.ensure_qt_fonts_registered()
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        font = QFont(font_family, int(font_size))
        font.setBold(bold)
        font.setItalic(italic)

        qcolor = QColor(color)

        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setFont(font)
            painter.setPen(qcolor)
            target = QRectF(0.0, 0.0, float(width), float(height))
            painter.drawText(
                target,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                text,
            )
        finally:
            painter.end()

        return pixmap

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_font_face_css(self, font_family: str) -> str:
        """Build ``@font-face`` CSS rules for all variants of *font_family*.

        File paths in ``src: url(...)`` use only the filename (no
        directory) because the ``fitz.Archive`` provides the directory
        context at insert time.
        """
        family_variants = self.FONT_MAP.get(font_family, {})
        rules: list[str] = []
        for variant, filename in family_variants.items():
            weight = "bold" if variant in ("bold", "bold_italic") else "normal"
            style = "italic" if variant in ("italic", "bold_italic") else "normal"
            rules.append(
                f"@font-face {{\n"
                f"  font-family: '{font_family}';\n"
                f"  src: url('{filename}');\n"
                f"  font-weight: {weight};\n"
                f"  font-style: {style};\n"
                f"}}"
            )
        return "\n".join(rules)


# ------------------------------------------------------------------
# Module-level utility
# ------------------------------------------------------------------

def _variant_key(bold: bool, italic: bool) -> str:
    """Map boolean bold/italic to a variant-map key."""
    if bold and italic:
        return "bold_italic"
    if bold:
        return "bold"
    if italic:
        return "italic"
    return "regular"
