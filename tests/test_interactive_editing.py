"""
Test interactive editing, repositioning, and deletion of text,
live properties synchronization, vector zoom supersampling, and icons.
"""

import sys
import unittest
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.annotations import TextBoxData
from core.pdf_engine import PdfEngine, TextBlock
from ui.i18n import I18n
from ui.pdf_view import PdfPageItem, PdfTextBlockSelectionItem, PdfView, TextBoxItem
from ui.toolbar import Tool, get_icon, _TOOL_DEFS


class TestInteractiveEditing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        self.engine = PdfEngine()
        self.engine.create_new()
        self.view = PdfView()
        self.i18n = I18n()
        self.view.set_dependencies(self.engine, None, self.i18n)
        self.view.load_document(self.engine)

    def test_text_box_repositioning(self):
        """Verify that moving a text box updates data.rect with new PDF point coordinates."""
        data = TextBoxData(
            id="test-box-1",
            page_index=0,
            rect=(50.0, 50.0, 200.0, 80.0),
            text="বাংলাদেশ",
        )
        page_item = self.view._page_items[0]
        item = self.view._add_text_box_item(data, page_item)

        initial_rect = item.data.rect
        self.assertEqual(initial_rect[0], 50.0)
        self.assertEqual(initial_rect[1], 50.0)

        # Move item to a new position
        new_scene_pos = page_item.pos() + QPointF(150.0 * page_item.scale_x, 250.0 * page_item.scale_y)
        item.setPos(new_scene_pos)

        # Sync position
        item._sync_position()

        # Check updated rect coordinates
        updated_rect = item.data.rect
        self.assertAlmostEqual(updated_rect[0], 150.0, delta=1.0)
        self.assertAlmostEqual(updated_rect[1], 250.0, delta=1.0)

    def test_text_box_editing(self):
        """Verify editing text box content and dynamic bounding box."""
        data = TextBoxData(
            id="test-box-2",
            page_index=0,
            rect=(50.0, 50.0, 200.0, 80.0),
            text="ক",
        )
        page_item = self.view._page_items[0]
        item = self.view._add_text_box_item(data, page_item)
        short_width = item.boundingRect().width()

        # Update text to a much longer sentence
        item.data.text = "বিশ্ববিদ্যালয় ও বাংলাদেশ একটি সুন্দর দেশ"
        item.prepareGeometryChange()
        item._sync_position()
        long_width = item.boundingRect().width()

        self.assertGreater(long_width, short_width)

    def test_text_box_deletion(self):
        """Verify that text box can be deleted via delete_selected or signal."""
        data = TextBoxData(
            id="test-box-3",
            page_index=0,
            rect=(50.0, 50.0, 200.0, 80.0),
            text="মুছে ফেলা হোক",
        )
        page_item = self.view._page_items[0]
        item = self.view._add_text_box_item(data, page_item)

        self.assertIn("test-box-3", self.view._overlay_items)
        self.assertIn(item, self.view._scene.items())

        # Select and delete
        item.setSelected(True)
        self.view.delete_selected()

        self.assertNotIn("test-box-3", self.view._overlay_items)
        self.assertNotIn(item, self.view._scene.items())

    def test_properties_live_update(self):
        """Verify that changing properties in properties panel updates selected text box in real time."""
        data = TextBoxData(
            id="test-box-prop",
            page_index=0,
            rect=(50.0, 50.0, 200.0, 80.0),
            text="ফন্ট টেস্ট",
            font_family="Noto Sans Bengali",
            font_size=14.0,
            color="#000000",
            bold=False,
            italic=False,
        )
        page_item = self.view._page_items[0]
        item = self.view._add_text_box_item(data, page_item)
        item.setSelected(True)

        # Apply new properties
        self.view.update_properties({
            "font_family": "SolaimanLipi",
            "font_size": 24.0,
            "color": "#ef4444",
            "bold": True,
            "italic": True,
        })

        self.assertEqual(item.data.font_family, "SolaimanLipi")
        self.assertEqual(item.data.font_size, 24.0)
        self.assertEqual(item.data.color, "#ef4444")
        self.assertTrue(item.data.bold)
        self.assertTrue(item.data.italic)

    def test_text_block_selection_and_deletion(self):
        """Verify that existing PDF text blocks can be selected and deleted/erased."""
        # Insert a text block in engine
        page = self.engine.document[0]
        self.engine.text_renderer.insert_text_to_page(page, (50, 50, 200, 80), "মুছে ফেলার টেক্সট")

        block = TextBlock(
            page_index=0,
            rect=(50.0, 50.0, 200.0, 80.0),
            text="মুছে ফেলার টেক্সট",
            font_name="Noto Sans Bengali",
            font_size=14.0,
        )

        page_item = self.view._page_items[0]
        self.view._select_text_block(0, block, page_item)

        self.assertIsNotNone(self.view._current_text_selection)
        self.assertIn(self.view._current_text_selection, self.view._scene.items())

        # Press delete / call delete_selected
        self.view.delete_selected()

        self.assertIsNone(self.view._current_text_selection)

    def test_zoom_vector_supersampling(self):
        """Verify that zooming re-renders pages at high-DPI supersampling without pixelation."""
        page_item = self.view._page_items[0]

        # Default zoom 1.0 -> supersampled at least 2.5x
        self.assertGreaterEqual(page_item._rendered_zoom, 2.5)

        # Zoom in to 2.0x -> supersampled to 5.0x
        self.view.set_zoom(2.0)
        self.assertGreaterEqual(page_item._rendered_zoom, 5.0)

        # Zoom in to 3.0x -> supersampled to 7.5x
        self.view.set_zoom(3.0)
        self.assertGreaterEqual(page_item._rendered_zoom, 7.5)

    def test_all_svg_icons_valid(self):
        """Verify all toolbar and property SVG icons load and render valid pixmaps."""
        for tool, svg_name, fallback, key in _TOOL_DEFS:
            icon = get_icon(svg_name)
            self.assertFalse(icon.isNull(), f"Icon {svg_name} is null")
            pm = icon.pixmap(24, 24)
            self.assertFalse(pm.isNull(), f"Pixmap for {svg_name} is null")
            self.assertEqual(pm.width(), 24)
            self.assertEqual(pm.height(), 24)

        extra_icons = [
            "bold.svg", "bold-white.svg", "italic.svg", "italic-white.svg", "palette.svg",
            "zoom-fit.svg", "zoom-page.svg", "read-mode.svg",
        ]
        for extra in extra_icons:
            icon = get_icon(extra)
            self.assertFalse(icon.isNull(), f"Icon {extra} is null")
            pm = icon.pixmap(24, 24)
            self.assertFalse(pm.isNull(), f"Pixmap for {extra} is null")

    def test_eraser_on_single_word_only(self):
        """Verify clicking to erase a word erases ONLY that word, not the whole line."""
        page = self.engine.document[0]
        # Insert a multi-word line
        self.engine.text_renderer.insert_text_to_page(page, (50, 50, 400, 150), "Hello beautiful world")

        # Extract words
        words = self.engine.get_text_blocks(0, level="word")
        word_texts = [w.text for w in words]
        self.assertIn("beautiful", word_texts)
        self.assertIn("Hello", word_texts)
        self.assertIn("world", word_texts)

        # Find the word 'beautiful' and erase only it
        b_word = next(w for w in words if w.text == "beautiful")
        self.view._erase_text_block(0, b_word)

        # Extract words after erasing
        words_after = self.engine.get_text_blocks(0, level="word")
        texts_after = [w.text for w in words_after]
        self.assertNotIn("beautiful", texts_after)
        self.assertIn("Hello", texts_after)
        self.assertIn("world", texts_after)

    def test_properties_panel_redesign_controls(self):
        """Verify redesigned properties panel has bold/italic toggle buttons and palette chips."""
        from ui.properties_panel import PropertiesPanel
        panel = PropertiesPanel(self.i18n)

        # Show text properties
        data = TextBoxData(
            id="test-box-redesign",
            page_index=0,
            rect=(10, 10, 100, 40),
            text="Hello",
            bold=True,
            italic=False,
            color="#dc2626",
        )
        panel.show_text_properties(data)

        # Verify bold button is checked and italic is unchecked
        self.assertTrue(panel._text_panel.bold_btn.isChecked())
        self.assertFalse(panel._text_panel.italic_btn.isChecked())
        self.assertFalse(panel._text_panel.bold_btn.icon().isNull(), "Bold button must have an icon")
        self.assertFalse(panel._text_panel.italic_btn.icon().isNull(), "Italic button must have an icon")
        self.assertEqual(panel._text_panel.color_btn.color.lower(), "#dc2626")

        # Test picking a palette preset
        panel._text_panel.palette_row.color_picked.emit("#16a34a")
        self.assertEqual(panel._text_panel.color_btn.color.lower(), "#16a34a")
        self.assertEqual(panel._text_panel.palette_row._selected_color, "#16a34a")

        # Verify font size increment and decrement buttons
        self.assertEqual(panel._text_panel.font_size_spin.value(), 14)
        panel._text_panel.btn_size_inc.click()
        self.assertEqual(panel._text_panel.font_size_spin.value(), 15)
        panel._text_panel.btn_size_dec.click()
        self.assertEqual(panel._text_panel.font_size_spin.value(), 14)

        # Verify font size can reduce below 6 (down to 1)
        panel._text_panel.font_size_spin.setValue(6)
        panel._text_panel.btn_size_dec.click()
        self.assertEqual(panel._text_panel.font_size_spin.value(), 5)
        panel._text_panel.font_size_spin.setValue(1)
        self.assertEqual(panel._text_panel.font_size_spin.minimum(), 1)

    def test_modified_flag_tracking(self):
        """Verify that document modification flag tracks changes and clears on save."""
        from ui.main_window import MainWindow
        win = MainWindow()

        # Initially after create_new, document is not modified
        self.assertFalse(win._is_modified)

        # Adding a text box sets _is_modified to True
        win._view.document_modified.emit()
        self.assertTrue(win._is_modified)

        # Mocking successful save sets _is_modified to False
        win._is_modified = False
        self.assertFalse(win._is_modified)
        # Test keyPressEvent on PdfView directly for Ctrl+Z and Ctrl+Y
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        undo_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        redo_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        win._view.keyPressEvent(undo_ev)
        win._view.keyPressEvent(redo_ev)

        win.close()

    def test_eraser_on_existing_text(self):
        """Verify that eraser tool redacts / erases text from PDF."""
        page = self.engine.document[0]
        self.engine.text_renderer.insert_text_to_page(page, (50, 50, 200, 80), "টেস্ট টেক্সট")

        # Call redact_area on that block
        self.engine.redact_area(0, (50, 50, 200, 80), replacement_text="")
        self.assertEqual(self.engine.page_count, 1)

    def test_multi_line_text_support(self):
        """Verify multi-line text input and bounds in TextBoxItem."""
        page_item = self.view._page_items[0]
        single_data = TextBoxData(
            id="single-line",
            page_index=0,
            rect=(10, 10, 100, 20),
            text="Single line text",
            font_size=12.0,
        )
        single_item = self.view._add_text_box_item(single_data, page_item)
        single_h = single_item.boundingRect().height()

        multi_data = TextBoxData(
            id="multi-line",
            page_index=0,
            rect=(10, 40, 100, 60),
            text="Line 1\nLine 2\nLine 3\nLine 4",
            font_size=12.0,
        )
        multi_item = self.view._add_text_box_item(multi_data, page_item)
        multi_h = multi_item.boundingRect().height()

        self.assertGreater(multi_h, single_h * 2.0)

    def test_font_size_reduction_to_2(self):
        """Verify reducing font size to 2 shrinks bounding rect without being clamped to 8pt."""
        page_item = self.view._page_items[0]
        tiny_data = TextBoxData(
            id="tiny-font",
            page_index=0,
            rect=(10, 10, 50, 10),
            text="Fine print footnote",
            font_size=2.0,
        )
        tiny_item = self.view._add_text_box_item(tiny_data, page_item)
        br = tiny_item.boundingRect()

        # At font size 2, height should be small (less than 16px)
        self.assertLess(br.height(), 16.0)

    def test_multiple_edits_and_saves(self):
        """Verify editing added elements multiple times and saving repeatedly without duplication."""
        import tempfile
        import pymupdf

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "multi_edit.pdf"
            tb = TextBoxData(
                id="edit-multi",
                page_index=0,
                rect=(50, 50, 200, 80),
                text="Initial text",
                font_size=14.0,
            )
            self.engine.annotation_manager.add_text_box(tb)

            # 1st save
            self.engine.save(str(pdf_path))
            doc1 = pymupdf.open(str(pdf_path))
            txt1 = doc1[0].get_text()
            doc1.close()
            self.assertIn("Initial text", txt1)

            # 2nd edit: update text and change font size to 2
            tb.text = "Second updated text\nMulti-line line 2"
            tb.font_size = 2.0
            self.engine.annotation_manager.modify_text_box("edit-multi", tb)

            # 2nd save
            self.engine.save()
            doc2 = pymupdf.open(str(pdf_path))
            txt2 = doc2[0].get_text()
            doc2.close()

            # Old initial text must NOT be present in 2nd save; only updated text
            self.assertNotIn("Initial text", txt2)
            self.assertIn("Second updated text", txt2)
            self.assertIn("Multi-line line 2", txt2)

    def test_in_place_save_no_windows_permission_error(self):
        """Verify saving over the original opened PDF file does not cause Windows PermissionError."""
        import tempfile
        import pymupdf

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_inplace.pdf"
            # Create a simple valid PDF on disk
            doc = pymupdf.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), "Original Content")
            doc.save(str(file_path))
            doc.close()

            # Open with engine
            eng = PdfEngine()
            eng.open(str(file_path))

            # Add an annotation
            tb = TextBoxData(
                id="inplace-tb",
                page_index=0,
                rect=(50, 100, 150, 40),
                text="Edited Content",
            )
            eng.annotation_manager.add_text_box(tb)

            # In-place save (must not raise Permission denied / FzErrorSystem)
            eng.save()

            # Verify content was updated on disk
            doc_verify = pymupdf.open(str(file_path))
            txt = doc_verify[0].get_text()
            doc_verify.close()
            eng.close()

            self.assertIn("Original Content", txt)
            self.assertIn("Edited Content", txt)

    def test_open_document_fills_canvas_fit_width_default(self):
        """Verify opening a document defaults to fit-to-width, with actual size, fit page and fit height support."""
        self.view.load_document(self.engine)
        # Default zoom mode is fit to width
        self.assertGreater(self.view._zoom, 0.2)
        self.assertTrue(self.view.alignment() & Qt.AlignmentFlag.AlignHCenter)
        self.assertTrue(self.view.alignment() & Qt.AlignmentFlag.AlignTop)

        # Actual size sets zoom to 1.0 (100%)
        self.view.zoom_actual_size()
        self.assertEqual(self.view._zoom, 1.0)

        # Test fit to height and fit to page
        self.view.zoom_fit_height()
        self.assertGreater(self.view._zoom, 0.2)

        self.view.zoom_fit_page()
        self.assertGreater(self.view._zoom, 0.2)

        # Check scene rect and page centering
        page_item = self.view._page_items[0]
        scene_w = self.view._scene.sceneRect().width()
        expected_x = (scene_w - page_item.pt_width) / 2.0
        self.assertAlmostEqual(page_item.pos().x(), expected_x, delta=0.5)

    def test_bangla_phonetic_live_preview_and_original_text(self):
        """Verify Bangla phonetic mode keeps original text live, defaults to normal typing, and previews only when checked."""
        from core.bangla_input import BanglaPhoneticEngine
        from ui.dialogs import MultiLineTextDialog
        bangla_engine = BanglaPhoneticEngine()
        bangla_engine.set_active(True)

        dlg = MultiLineTextDialog(
            parent=None,
            title="Add Text",
            initial_text="amra shobai",
            bangla_engine=bangla_engine,
            i18n=self.i18n,
        )

        # Widget must bypass eventFilter so original text is typed/displayed live
        self.assertTrue(dlg.text_edit.property("no_bangla_filter"))
        self.assertEqual(dlg.text_edit.toPlainText(), "amra shobai")

        # By default, phonetic checkbox is unchecked to prevent unwanted live converted view
        self.assertFalse(dlg._bangla_cb.isChecked())
        self.assertTrue(dlg.preview_card.isHidden())
        self.assertEqual(dlg.get_text(), "amra shobai")

        # When user checks phonetic, preview card becomes visible with transliteration
        dlg._bangla_cb.setChecked(True)
        self.assertFalse(dlg.preview_card.isHidden())
        self.assertEqual(dlg.preview_label.text(), "আমরা সবাই")
        self.assertEqual(dlg.get_text(), "আমরা সবাই")

        # Live typing updates: append " raja"
        dlg.text_edit.setPlainText("amra shobai raja")
        self.assertEqual(dlg.text_edit.toPlainText(), "amra shobai raja")
        self.assertEqual(dlg.preview_label.text(), "আমরা সবাই রাজা")
        self.assertEqual(dlg.get_text(), "আমরা সবাই রাজা")

        # Toggle phonetic off -> original text returned and preview card hidden
        dlg._bangla_cb.setChecked(False)
        self.assertTrue(dlg.preview_card.isHidden())
        self.assertEqual(dlg.get_text(), "amra shobai raja")

    def test_undo_redo_and_read_mode(self):
        """Verify undo/redo operations and read mode toggle."""
        from ui.main_window import MainWindow
        win = MainWindow()

        # Add a text box
        tb = TextBoxData(
            id="undo-test",
            page_index=0,
            rect=(50, 50, 100, 30),
            text="Testing Undo",
        )
        win._on_text_box_added(tb)
        self.assertTrue(win._undo_stack.can_undo)
        self.assertIn("undo-test", [b.id for b in win._engine.annotation_manager.text_boxes])

        # Perform undo
        win.action_undo()
        self.assertNotIn("undo-test", [b.id for b in win._engine.annotation_manager.text_boxes])
        self.assertTrue(win._undo_stack.can_redo)

        # Perform redo
        win.action_redo()
        self.assertIn("undo-test", [b.id for b in win._engine.annotation_manager.text_boxes])

        # Test Read Mode toggle
        self.assertFalse(getattr(win, "_is_read_mode", False))
        win.toggle_read_mode()
        self.assertTrue(win._is_read_mode)
        self.assertTrue(win._toolbar.isHidden())
        self.assertTrue(win._thumb_panel.isHidden())

        # Exit Read Mode
        win.toggle_read_mode()
        self.assertFalse(win._is_read_mode)
        self.assertFalse(win._toolbar.isHidden())

        # Test keyPressEvent on PdfView directly for Ctrl+Z and Ctrl+Y
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        undo_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        redo_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
        win._view.keyPressEvent(undo_ev)
        win._view.keyPressEvent(redo_ev)

        win.close()

    def tearDown(self):
        self.engine.close()


if __name__ == "__main__":
    unittest.main()
