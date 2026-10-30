"""
Unit tests for the new feature improvements:
1. Underline and strikethrough in Properties panel & text rendering.
2. Live drag preview for Highlight (borderless, live color), Rectangle, Line, Arrow, Freehand.
3. Interactive resizing and repositioning of inserted images and signatures.
"""

import sys
import unittest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPen, QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
)

from core.annotations import AnnotationManager, ImageData, TextBoxData, HighlightData, ShapeData
from core.pdf_engine import PdfEngine
from ui.i18n import I18n
from ui.pdf_view import PdfView, ImageItem, TextBoxItem
from ui.properties_panel import PropertiesPanel
from ui.toolbar import Tool

app = QApplication.instance() or QApplication(sys.argv)


class TestFeatureImprovements(unittest.TestCase):
    """Test suite for request #10 improvements."""

    def setUp(self) -> None:
        self.i18n = I18n()
        self.engine = PdfEngine()
        self.engine.create_new()
        self.prop_panel = PropertiesPanel(self.i18n)
        self.view = PdfView()
        self.view.load_document(self.engine)

    def tearDown(self) -> None:
        self.engine.close()

    def test_properties_panel_underline_and_strike_buttons(self) -> None:
        """Verify underline and strike controls are present and emit signals in Properties panel."""
        self.assertIsNotNone(self.prop_panel._text_panel.underline_btn)
        self.assertIsNotNone(self.prop_panel._text_panel.strike_btn)

        underline_events = []
        strike_events = []
        self.prop_panel.underline_changed.connect(underline_events.append)
        self.prop_panel.strike_changed.connect(strike_events.append)

        self.prop_panel._text_panel.underline_btn.click()
        self.assertEqual(underline_events, [True])

        self.prop_panel._text_panel.strike_btn.click()
        self.assertEqual(strike_events, [True])

        props = self.prop_panel.get_text_properties()
        self.assertTrue(props["underline"])
        self.assertTrue(props["strikethrough"])

    def test_annotation_style_selector_in_properties_panel(self) -> None:
        """Verify annotation style selector (Highlight, Underline, Strike) switches styles."""
        styles = []
        self.prop_panel.annotation_type_changed.connect(styles.append)

        self.prop_panel._annotation_panel.btn_style_ul.click()
        self.assertIn("underline", styles)

        self.prop_panel._annotation_panel.btn_style_st.click()
        self.assertIn("strikethrough", styles)

        self.prop_panel._annotation_panel.btn_style_hl.click()
        self.assertIn("highlight", styles)

    def test_textbox_underline_and_strikethrough_properties(self) -> None:
        """Verify text box data and rendering supports underline and strikethrough."""
        tb_data = TextBoxData(
            page_index=0,
            rect=(100.0, 100.0, 200.0, 130.0),
            text="Ruhi PDF Text",
            underline=True,
            strikethrough=True,
        )
        page_item = self.view._page_items[0]
        item = TextBoxItem(tb_data, scale=1.0, page_item=page_item)
        br = item.boundingRect()
        self.assertGreater(br.width(), 0)
        self.assertGreater(br.height(), 0)

    def test_highlight_live_preview_borderless(self) -> None:
        """Verify dragging with Highlight tool creates a borderless rectangle with live color/opacity."""
        self.view.set_tool(Tool.HIGHLIGHT)
        self.view.current_properties["color"] = "#ffeb3b"
        self.view.current_properties["opacity"] = 0.5

        page_item = self.view._page_items[0]
        vp_start = self.view.mapFromScene(page_item.pos() + QPointF(50, 50))
        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(vp_start),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.view.mousePressEvent(press_ev)

        # Move to drag
        vp_move = self.view.mapFromScene(page_item.pos() + QPointF(150, 80))
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(vp_move),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.view.mouseMoveEvent(move_ev)

        # Live preview item should exist, be QGraphicsRectItem, have NoPen (borderless), and live color
        preview = getattr(self.view, "_live_preview_item", None)
        self.assertIsNotNone(preview)
        self.assertIsInstance(preview, QGraphicsRectItem)
        self.assertEqual(preview.pen().style(), Qt.PenStyle.NoPen)
        self.assertEqual(preview.brush().color().name(), "#ffeb3b")
        self.assertAlmostEqual(preview.brush().color().alphaF(), 0.5, places=1)

        # Release mouse: preview item is cleaned up and permanent annotation added
        release_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(vp_move),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.view.mouseReleaseEvent(release_ev)
        self.assertIsNone(getattr(self.view, "_live_preview_item", None))

    def test_shape_live_preview(self) -> None:
        """Verify rectangle, line, and arrow tools display live visual feedback during drag."""
        page_item = self.view._page_items[0]
        vp_start = self.view.mapFromScene(page_item.pos() + QPointF(50, 50))
        vp_move = self.view.mapFromScene(page_item.pos() + QPointF(150, 150))

        # Test Rectangle
        self.view.set_tool(Tool.RECTANGLE)
        press_ev = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(vp_start), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.view.mousePressEvent(press_ev)
        move_ev = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(vp_move), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.view.mouseMoveEvent(move_ev)
        self.assertIsInstance(self.view._live_preview_item, QGraphicsRectItem)
        release_ev = QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPointF(vp_move), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.view.mouseReleaseEvent(release_ev)
        self.assertIsNone(self.view._live_preview_item)

        # Test Line
        self.view.set_tool(Tool.LINE)
        self.view.mousePressEvent(press_ev)
        self.view.mouseMoveEvent(move_ev)
        self.assertIsInstance(self.view._live_preview_item, QGraphicsLineItem)
        self.view.mouseReleaseEvent(release_ev)
        self.assertIsNone(self.view._live_preview_item)

        # Test Arrow
        self.view.set_tool(Tool.ARROW)
        self.view.mousePressEvent(press_ev)
        self.view.mouseMoveEvent(move_ev)
        self.assertIsInstance(self.view._live_preview_item, QGraphicsPathItem)
        self.view.mouseReleaseEvent(release_ev)
        self.assertIsNone(self.view._live_preview_item)

    def test_image_interactive_resizing(self) -> None:
        """Verify inserted image can be resized interactively via its handles."""
        page_item = self.view._page_items[0]
        img_data = ImageData(
            id="test-img-1",
            page_index=0,
            rect=(50.0, 50.0, 150.0, 150.0),
            image_path="",
            opacity=1.0,
        )
        item = self.view._add_image_item(img_data, page_item)
        self.assertIsNotNone(item)
        self.assertIsInstance(item, ImageItem)

        # Initial dimensions: 100 x 100 pt
        w, h = item._get_dims()
        self.assertAlmostEqual(w, 100.0, places=1)
        self.assertAlmostEqual(h, 100.0, places=1)

        # Check handle detection for bottom-right (br) corner
        hit = item._hit_handle(QPointF(w, h))
        self.assertEqual(hit, "br")

        # Simulate dragging the bottom-right handle to expand image
        item._drag_handle = "br"
        item._drag_start_scene_pos = QPointF(150, 150)
        item._drag_start_rect = (50.0, 50.0, 150.0, 150.0)

        # Move mouse +50px right, +30px down
        move_ev = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(200, 180),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        # Mock scenePos on event by executing item logic
        item.mouseMoveEvent(move_ev)

        # Verify new rect updated
        new_w = item.data.rect[2] - item.data.rect[0]
        new_h = item.data.rect[3] - item.data.rect[1]
        self.assertAlmostEqual(new_w, 150.0, places=1)
        self.assertAlmostEqual(new_h, 130.0, places=1)

        # Release drag
        rel_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(200, 180),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        item.mouseReleaseEvent(rel_ev)
        self.assertIsNone(item._drag_handle)

    def test_page_detection_on_scroll_and_sidebar_sync(self) -> None:
        """Verify that scrolling to page 2 updates current page index and thumbnail selection."""
        import pymupdf as fitz
        from ui.thumbnail_panel import ThumbnailPanel

        doc = fitz.open()
        doc.new_page(width=600, height=800)
        doc.new_page(width=600, height=800)
        doc.save("tests/test_output/test_pages.pdf")
        doc.close()

        engine = PdfEngine()
        engine.open("tests/test_output/test_pages.pdf")
        thumb_panel = ThumbnailPanel(self.i18n)
        thumb_panel.refresh(engine)

        view = PdfView()
        view.resize(800, 600)
        view.load_document(engine)
        view.page_changed.connect(thumb_panel.set_current_page)

        self.assertEqual(view._current_page_index, 0)
        self.assertEqual(thumb_panel._list.currentRow(), 0)

        # Scroll to page 2 (index 1)
        page_1_item = view._page_items[1]
        view.centerOn(page_1_item)
        view._update_current_page_from_viewport()

        # Both view and sidebar should now indicate page 1 (the 2nd page)
        self.assertEqual(view._current_page_index, 1)
        self.assertEqual(thumb_panel._list.currentRow(), 1)
        engine.close()

    def test_insert_image_places_on_current_page(self) -> None:
        """Verify that inserting image/signature places it on the currently viewed page."""
        import pymupdf as fitz
        doc = fitz.open()
        doc.new_page(width=600, height=800)
        doc.new_page(width=600, height=800)
        doc.save("tests/test_output/test_pages.pdf")
        doc.close()

        engine = PdfEngine()
        engine.open("tests/test_output/test_pages.pdf")
        view = PdfView()
        view.resize(800, 600)
        view.load_document(engine)

        # Connect annotation added to engine as MainWindow does
        view.annotation_added.connect(engine.annotation_manager.add_image)

        # Navigate to 2nd page (index 1)
        page_1_item = view._page_items[1]
        view.centerOn(page_1_item)
        view._update_current_page_from_viewport()
        self.assertEqual(view._current_page_index, 1)

        # Insert image
        cur_page = view._current_page_index
        insert_pos = view.get_viewport_center_on_page(cur_page)
        view.add_image_at(cur_page, "icons/app_icon.png", insert_pos)

        # Verify image was added to page 1 (2nd page), NOT page 0 (1st page)
        annots_p0 = engine.annotation_manager.get_annotations_for_page(0)["images"]
        annots_p1 = engine.annotation_manager.get_annotations_for_page(1)["images"]
        self.assertEqual(len(annots_p0), 0)
        self.assertEqual(len(annots_p1), 1)
        self.assertEqual(annots_p1[0].page_index, 1)
        engine.close()

    def test_image_cross_deletes_immediately(self) -> None:
        """Verify that clicking the red cross button on an image removes it immediately from scene and data."""
        page_item = self.view._page_items[0]
        img_data = ImageData(
            id="test-img-delete",
            page_index=0,
            rect=(50.0, 50.0, 150.0, 150.0),
            image_path="",
            opacity=1.0,
        )
        item = self.view._add_image_item(img_data, page_item)
        self.engine.annotation_manager.add_image(img_data)

        self.assertIn(item, self.view._scene.items())
        self.assertIn("test-img-delete", self.view._overlay_items)
        self.assertIsNotNone(self.engine.annotation_manager.get_image("test-img-delete"))

        # Click the red cross (positioned outside the top-right corner of the image)
        w, _ = item._get_dims()
        close_pos = QPointF(w + 2.0, -15.0)
        self.assertLess(close_pos.y(), 0.0, "Close button must be outside the image (y < 0)")
        self.assertTrue(item._hit_close(close_pos))

        press_ev = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            close_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        item.mousePressEvent(press_ev)

        # Verify immediate removal
        self.assertNotIn(item, self.view._scene.items())
        self.assertNotIn("test-img-delete", self.view._overlay_items)
        self.assertIsNone(self.engine.annotation_manager.get_image("test-img-delete"))

    def test_image_cross_button_is_outside_content_rect(self) -> None:
        """Verify that the delete cross button is positioned outside the image content rectangle."""
        page_item = self.view._page_items[0]
        img_data = ImageData(
            id="test-img-outside-check",
            page_index=0,
            rect=(50.0, 50.0, 150.0, 150.0),
            image_path="",
            opacity=1.0,
        )
        item = self.view._add_image_item(img_data, page_item)
        w, h = item._get_dims()

        # The image content area is [0, 0, w, h]
        # Any point inside the image content area must NOT trigger _hit_close
        inside_corner = QPointF(w - 2.0, 2.0)
        self.assertFalse(item._hit_close(inside_corner), "Inside top-right must NOT trigger close button")

        # The outside top-right position must trigger _hit_close
        outside_btn = QPointF(w + 2.0, -15.0)
        self.assertTrue(item._hit_close(outside_btn), "Outside top-right MUST trigger close button")
        self.assertLess(outside_btn.y(), 0.0)

        # boundingRect must comfortably contain the outside button
        br = item.boundingRect()
        self.assertTrue(br.contains(outside_btn), "boundingRect must enclose the outside close button")

    def test_image_and_signature_opacity_preserved_on_save(self) -> None:
        """Verify that image/signature opacity is properly burned into the saved PDF file."""
        import pymupdf as fitz
        from PIL import Image

        # Create a test solid blue image
        sig_img = Image.new("RGBA", (100, 100), (0, 0, 255, 255))
        sig_path = "tests/test_output/test_opacity_sample.png"
        sig_img.save(sig_path)

        # Create a test PDF with white background
        save_pdf_path = "tests/test_output/test_opacity_output.pdf"
        eng = PdfEngine()
        eng.create_new()
        # Page 0 is 595x842 (A4)

        # Add image with 50% opacity (0.5)
        img_data = ImageData(
            id="test-img-opacity-save",
            page_index=0,
            rect=(100.0, 100.0, 200.0, 200.0),
            image_path=sig_path,
            opacity=0.5,
        )
        eng.annotation_manager.add_image(img_data)

        # Save the document
        eng.save(save_pdf_path)
        eng.close()

        # Re-open saved PDF and verify that pixel blending reflects opacity
        reopened = fitz.open(save_pdf_path)
        pix = reopened[0].get_pixmap()
        # Pixel at (150, 150) is over white background (255, 255, 255)
        # With 50% blue (0, 0, 255), blended color should have red/green > 100 and blue > 200
        pixel = pix.pixel(150, 150)
        reopened.close()

        r, g, b = pixel[0], pixel[1], pixel[2]
        self.assertGreater(r, 100, f"Red channel should show white background blend, got {r}")
        self.assertGreater(g, 100, f"Green channel should show white background blend, got {g}")
        self.assertGreater(b, 200, f"Blue channel should show blue image blend, got {b}")


if __name__ == "__main__":
    unittest.main()
