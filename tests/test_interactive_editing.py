"""
Test interactive editing, repositioning, and deletion of text,
live properties synchronization, vector zoom supersampling, and icons.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.annotations import TextBoxData
from core.pdf_engine import PdfEngine, TextBlock
from ui.i18n import I18n
from ui.pdf_view import InlineCanvasTextEditor, PdfPageItem, PdfTextBlockSelectionItem, PdfView, TextBoxItem
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
        for def_tuple in _TOOL_DEFS:
            svg_name = def_tuple[1]
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
        self.assertEqual(self.view._fit_mode, "width")
        self.assertGreater(self.view._zoom, 0.2)
        self.assertTrue(self.view.alignment() & Qt.AlignmentFlag.AlignHCenter)
        self.assertTrue(self.view.alignment() & Qt.AlignmentFlag.AlignTop)

        # Actual size sets zoom to 1.0 (100%) and switches to manual mode
        self.view.zoom_actual_size()
        self.assertEqual(self.view._zoom, 1.0)
        self.assertEqual(self.view._fit_mode, "manual")

        # Test fit to height and fit to page
        self.view.zoom_fit_height()
        self.assertEqual(self.view._fit_mode, "height")
        self.assertGreater(self.view._zoom, 0.2)

        self.view.zoom_fit_page()
        self.assertEqual(self.view._fit_mode, "page")
        self.assertGreater(self.view._zoom, 0.2)

        # Zoom fit width restores fit mode to width
        self.view.zoom_fit_width()
        self.assertEqual(self.view._fit_mode, "width")

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

    def test_fonts_nikosh_solaimanlipi_kalpurush_available(self):
        """Verify Nikosh, SolaimanLipi, and Kalpurush font files are present and registered."""
        import os
        fonts_dir = Path(__file__).parent.parent / "fonts"
        self.assertTrue((fonts_dir / "Nikosh.ttf").exists(), "Nikosh.ttf must exist")
        self.assertTrue((fonts_dir / "SolaimanLipi.ttf").exists(), "SolaimanLipi.ttf must exist")
        self.assertTrue((fonts_dir / "Kalpurush.ttf").exists(), "Kalpurush.ttf must exist")

        families = self.engine.text_renderer.get_font_families()
        self.assertIn("Nikosh", families)
        self.assertIn("SolaimanLipi", families)
        self.assertIn("Kalpurush", families)

    def test_system_font_option_in_properties_panel(self):
        """Verify system font button and font selection in PropertiesPanel."""
        from ui.properties_panel import PropertiesPanel
        prop = PropertiesPanel(self.i18n)
        self.assertTrue(hasattr(prop._text_panel, "btn_system_font"))
        self.assertEqual(prop._text_panel.btn_system_font.objectName(), "SystemFontBtn")

        # Test set_font_families populates bundled and system fonts
        bundled = ["Noto Sans Bengali", "Kalpurush", "SolaimanLipi", "Nikosh", "Noto Sans"]
        prop.set_font_families(bundled)
        combo_items = [prop._text_panel.font_combo.itemText(i) for i in range(prop._text_panel.font_combo.count())]
        for b in bundled:
            self.assertIn(b, combo_items)
        # Should also include system fonts (e.g., Arial)
        self.assertIn("Arial", combo_items)

        # Test show_text_properties with custom/system font adds it to combo if not present
        tb_data = TextBoxData(
            id="sys-font-box",
            page_index=0,
            rect=(10, 10, 50, 30),
            text="Hello System",
            font_family="Georgia",
            font_size=18.0,
            bold=True,
            italic=True,
            color="#dc2626",
        )
        prop.show_text_properties(tb_data)
        self.assertEqual(prop._text_panel.font_combo.currentText(), "Georgia")
        self.assertEqual(prop._text_panel.font_size_spin.value(), 18)
        self.assertTrue(prop._text_panel.bold_btn.isChecked())
        self.assertTrue(prop._text_panel.italic_btn.isChecked())
        self.assertEqual(prop._text_panel.color_btn.color.lower(), "#dc2626")

    def test_auto_detect_font_features_from_pdf(self):
        """Verify get_text_blocks auto-detects font name, size, bold, italic, and color from PDF spans."""
        # Create a document and insert text with known font properties
        doc = self.engine.document
        page = doc[0]
        # Insert a red text word
        page.insert_text(
            (72, 100),
            "ReportTitle",
            fontname="helv",
            fontsize=20.0,
            color=(1.0, 0.0, 0.0),
        )

        blocks = self.engine.get_text_blocks(0, level="word")
        found = None
        for b in blocks:
            if "ReportTitle" in b.text:
                found = b
                break

        self.assertIsNotNone(found, "Word 'ReportTitle' should be detected")
        self.assertEqual(found.font_name, "Arial")  # Helv maps to Arial
        self.assertAlmostEqual(found.font_size, 20.0, delta=1.0)
        self.assertEqual(found.color.lower(), "#ff0000")

    def test_inline_editing_for_english(self):
        """Verify inline editor component behavior and direct inline canvas trigger."""
        from ui.pdf_view import InlineCanvasTextEditor
        editor = InlineCanvasTextEditor("InitialWord")
        self.assertEqual(editor.text(), "InitialWord")
        self.assertTrue(editor.property("no_bangla_filter"))

        # Test width expansion
        initial_w = editor.width()
        editor.setText("A very long sentence to test dynamic width expansion")
        editor._adjust_width(editor.text())
        self.assertGreater(editor.width(), initial_w)

        # Test commit signal
        committed_text = []
        editor.committed.connect(lambda t: committed_text.append(t))
        editor.commit()
        self.assertEqual(committed_text, ["A very long sentence to test dynamic width expansion"])

        # Test direct inline editing trigger on PdfView
        block = TextBlock(
            page_index=0,
            rect=(50.0, 50.0, 150.0, 75.0),
            text="EnglishWord",
            font_name="Arial",
            font_size=16.0,
            bold=True,
            italic=False,
            color="#0284c7",
        )
        self.view._start_inline_editing_block(0, block)
        proxies = [it for it in self.view._scene.items() if hasattr(it, "widget") and isinstance(it.widget(), InlineCanvasTextEditor)]
        self.assertGreaterEqual(len(proxies), 1)

        # Commit edit
        inline_ed = proxies[0].widget()
        inline_ed.setText("UpdatedWord")
        inline_ed.commit()

        # Check proxy removed after commit
        self.assertIsNone(proxies[0].scene())

    def test_double_click_english_and_bangla_opens_text_edit_dialog(self):
        """Verify that double clicking an English or Bangla word opens the text edit window (MultiLineTextDialog)."""
        from unittest.mock import patch, MagicMock
        from ui.dialogs import MultiLineTextDialog
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent, QPoint

        # Mock engine text block at (100, 100, 180, 120)
        eng_block = TextBlock(
            page_index=0,
            rect=(100.0, 100.0, 180.0, 120.0),
            text="EnglishText",
            font_name="Arial",
            font_size=14.0,
            bold=True,
            italic=False,
            color="#ff0000",
        )
        self.engine.get_text_blocks = MagicMock(return_value=[eng_block])

        # Test double clicking English word opens MultiLineTextDialog
        with patch('ui.pdf_view.MultiLineTextDialog') as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = True
            mock_dlg.get_text.return_value = "ReplacementEnglish"
            mock_dlg_cls.return_value = mock_dlg

            # Position mouse inside the word rect on page 0
            page_item = self.view._page_items[0]
            scene_pos = page_item.pos() + QPointF(110.0, 110.0)
            view_pos = self.view.mapFromScene(scene_pos)

            dbl_ev = QMouseEvent(
                QEvent.Type.MouseButtonDblClick,
                QPointF(view_pos),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            self.view.mouseDoubleClickEvent(dbl_ev)

            mock_dlg_cls.assert_called_once()
            call_kwargs = mock_dlg_cls.call_args.kwargs
            self.assertEqual(call_kwargs.get("initial_text"), "EnglishText")

        # Verify properties panel was synced to auto-detected font features
        self.assertEqual(self.view.current_properties["font_size"], 14.0)
        self.assertEqual(self.view.current_properties["bold"], True)
        self.assertEqual(self.view.current_properties["color"], "#ff0000")

    def test_arrow_key_positioning(self):
        """Verify positioning text boxes with arrow keys (1 pt fine, 10 pt coarse with Shift)."""
        data = TextBoxData(
            id="nudge-box",
            page_index=0,
            rect=(100.0, 100.0, 160.0, 120.0),
            text="Position Me",
        )
        page_item = self.view._page_items[0]
        item = self.view._add_text_box_item(data, page_item)
        self.view._scene.clearSelection()
        item.setSelected(True)
        item.setFocus()

        orig_pos = item.pos()

        # Press Right Arrow (1 pt nudge)
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        right_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        item.keyPressEvent(right_ev)
        self.assertEqual(item.pos().x(), orig_pos.x() + 1.0)
        self.assertEqual(item.pos().y(), orig_pos.y())

        # Press Down Arrow with Shift (10 pt nudge)
        down_shift_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
        item.keyPressEvent(down_shift_ev)
        self.assertEqual(item.pos().y(), orig_pos.y() + 10.0)

        # Also test via PdfView.keyPressEvent
        up_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        self.view.keyPressEvent(up_ev)
        self.assertEqual(item.pos().y(), orig_pos.y() + 9.0)

        # Test Backspace key on focused TextBoxItem deletes it
        del_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        item.keyPressEvent(del_ev)
        self.assertNotIn("nudge-box", self.view._overlay_items)

    def test_backspace_inline_deletes_word(self):
        """Verify that backspacing text to empty in inline editor or dialog erases/deletes the word."""
        from ui.pdf_view import InlineCanvasTextEditor
        from unittest.mock import patch
        from ui.dialogs import MultiLineTextDialog

        block = TextBlock(
            page_index=0,
            rect=(50.0, 80.0, 120.0, 100.0),
            text="WordToDelete",
            font_name="Arial",
            font_size=12.0,
            bold=False,
            italic=False,
            color="#000000",
        )
        # Test inline editor clearing deletes word
        self.view._start_inline_editing_block(0, block)
        proxies = [it for it in self.view._scene.items() if hasattr(it, "widget") and isinstance(it.widget(), InlineCanvasTextEditor)]
        self.assertEqual(len(proxies), 1)
        editor = proxies[0].widget()
        editor.setText("")
        editor.commit()
        self.assertIsNone(proxies[0].scene())

        # Test MultiLineTextDialog clearing deletes word via _redact_and_replace_block
        with patch.object(MultiLineTextDialog, 'exec', return_value=True):
            with patch.object(MultiLineTextDialog, 'get_text', return_value=""):
                with patch.object(self.view, '_erase_text_block') as mock_erase:
                    self.view._redact_and_replace_block(0, block)
                    mock_erase.assert_called_once_with(0, block)

    def test_original_font_size_applied_consistently(self):
        """Verify replacement text retains original font size (e.g. 10.5 pt) for consistency."""
        from unittest.mock import patch
        from ui.dialogs import MultiLineTextDialog
        from ui.pdf_view import InlineCanvasTextEditor

        block = TextBlock(
            page_index=0,
            rect=(50.0, 80.0, 120.0, 100.0),
            text="ConsistentSize",
            font_name="Times New Roman",
            font_size=10.5,
            bold=True,
            italic=False,
            color="#000000",
        )
        # Even if current_properties font_size is set to 24.0:
        self.view.current_properties["font_size"] = 24.0

        # Verify inline editor maintains 10.5 pt
        self.view._start_inline_editing_block(0, block)
        proxies = [it for it in self.view._scene.items() if hasattr(it, "widget") and isinstance(it.widget(), InlineCanvasTextEditor)]
        self.assertEqual(len(proxies), 1)
        editor = proxies[0].widget()
        self.assertEqual(editor.point_size, 10.5)
        editor.setText("ReplacedConsistent")
        editor.commit()

        # Verify _redact_and_replace_block with dialog retains 10.5 pt
        with patch.object(MultiLineTextDialog, 'exec', return_value=True):
            with patch.object(MultiLineTextDialog, 'get_text', return_value="DialogReplaced"):
                with patch.object(self.engine, 'redact_area') as mock_redact:
                    self.view._redact_and_replace_block(0, block)
                    mock_redact.assert_called_once()
                    call_kwargs = mock_redact.call_args.kwargs
                    self.assertEqual(call_kwargs.get("font_size"), 10.5)
                    self.assertEqual(call_kwargs.get("font_family"), "Times New Roman")
                    self.assertEqual(call_kwargs.get("bold"), True)

    def test_welcome_screen_and_recent_files_history(self):
        """Verify WelcomeScreen, DragDropZone, and RecentFilesManager capping at 10 items."""
        from ui.welcome_screen import RecentFilesManager, WelcomeScreen

        # Clear existing history
        RecentFilesManager.clear_recent_files()
        self.assertEqual(RecentFilesManager.get_recent_files(), [])

        # Add 12 files to verify maximum cap of 10
        for i in range(12):
            RecentFilesManager.add_recent_file(f"C:/fake_path/file_{i}.pdf")

        recent = RecentFilesManager.get_recent_files()
        self.assertEqual(len(recent), 10)
        # Most recent should be file_11
        self.assertIn("file_11.pdf", recent[0]["name"])

        # Test WelcomeScreen UI rendering
        welcome = WelcomeScreen(self.i18n)
        self.assertEqual(welcome.recent_container.count(), 10)

        # Test file selected signal
        from unittest.mock import patch
        selected_paths = []
        welcome.file_selected.connect(lambda p: selected_paths.append(p))
        with patch("ui.welcome_screen.QMessageBox.warning") as mock_warn:
            welcome._on_file_chosen("C:/fake_path/file_11.pdf")
            mock_warn.assert_called_once()
        # Since it doesn't exist on disk, it pops a warning and removes it
        self.assertEqual(len(RecentFilesManager.get_recent_files()), 9)

        # Test clear
        RecentFilesManager.clear_recent_files()
        self.assertEqual(len(RecentFilesManager.get_recent_files()), 0)

    def test_toolbar_icon_labels_and_close_button(self):
        """Verify that toolbar buttons have single-word text labels under icons, compact font size, and functional Close."""
        from ui.toolbar import EditorToolBar, Tool
        toolbar = EditorToolBar(self.i18n)
        self.assertEqual(toolbar.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        # Check Close action exists and has single-word label "Close"
        self.assertTrue(hasattr(toolbar, "_close_action"))
        self.assertEqual(toolbar._close_action.text(), "Close")
        self.assertNotIn(" ", toolbar._close_action.text().strip())

        # Check all tools have single-word, non-empty text labels
        for tool, action in toolbar._tool_actions.items():
            self.assertTrue(bool(action.text()), f"Tool {tool} must have a label")
            self.assertNotIn(" ", action.text().strip(), f"Tool {tool} label '{action.text()}' must be a single word")

        # Check all file, zoom, and mode actions also have single-word labels
        all_actions = [
            toolbar._open_action,
            toolbar._save_action,
            toolbar._close_action,
            toolbar._undo_action,
            toolbar._redo_action,
            toolbar._delete_action,
            toolbar._zoom_in_action,
            toolbar._zoom_out_action,
            toolbar._zoom_fit_action,
            toolbar._zoom_page_action,
            toolbar._read_mode_action,
            toolbar._bangla_action,
        ]
        for action in all_actions:
            self.assertNotIn(" ", action.text().strip(), f"Action label '{action.text()}' must be a single word")

        # Verify stylesheet sets compact 10px font size
        self.assertIn("10px", toolbar.styleSheet())

        # Signal check
        close_emitted = []
        toolbar.close_requested.connect(lambda: close_emitted.append(True))
        toolbar._close_action.trigger()
        self.assertEqual(close_emitted, [True])

    def test_zero_shift_and_selection_cleanup_on_cancel_and_ok(self):
        """Verify that closing redact/replace dialog on Cancel or OK clears selection and preserves scroll."""
        from unittest.mock import patch
        from ui.dialogs import MultiLineTextDialog

        block = TextBlock(
            page_index=0,
            rect=(60.0, 60.0, 140.0, 80.0),
            text="ShiftTestWord",
            font_name="Arial",
            font_size=12.0,
            bold=False,
            italic=False,
            color="#000000",
        )
        # Set scrollbar to a valid position within its range
        self.view.horizontalScrollBar().setValue(min(20, self.view.horizontalScrollBar().maximum()))
        self.view.verticalScrollBar().setValue(min(50, self.view.verticalScrollBar().maximum()))
        orig_h = self.view.horizontalScrollBar().value()
        orig_v = self.view.verticalScrollBar().value()

        # Test Cancel: dlg.exec() returns False
        with patch.object(MultiLineTextDialog, 'exec', return_value=False):
            self.view._redact_and_replace_block(0, block)

        # Selection item must be cleaned up on Cancel
        self.assertIsNone(self.view._current_text_selection)
        # Scrollbars must not shift
        self.assertEqual(self.view.horizontalScrollBar().value(), orig_h)
        self.assertEqual(self.view.verticalScrollBar().value(), orig_v)

    def test_save_overwrite_warning_dialog(self):
        """Verify warning dialog when clicking Save on an existing PDF to prevent accidental overwrite."""
        from ui.main_window import MainWindow
        from unittest.mock import patch, MagicMock

        win = MainWindow()
        win._engine._file_path = "C:/test_docs/report.pdf"
        win._engine.save = MagicMock()
        win._is_modified = True

        # Case 1: User cancels -> do not overwrite, remains modified
        with patch("ui.main_window.QMessageBox") as mock_box_cls:
            mock_box = MagicMock()
            btn_overwrite = MagicMock()
            btn_save_as = MagicMock()
            btn_cancel = MagicMock()
            mock_box.addButton.side_effect = [btn_overwrite, btn_save_as, btn_cancel]
            mock_box.clickedButton.return_value = btn_cancel
            mock_box_cls.return_value = mock_box

            result = win.action_save()
            self.assertFalse(result)
            win._engine.save.assert_not_called()
            self.assertTrue(win._is_modified)

        # Case 2: User confirms overwrite -> saves to original file, modified cleared
        with patch("ui.main_window.QMessageBox") as mock_box_cls:
            mock_box = MagicMock()
            mock_box.addButton.side_effect = [btn_overwrite, btn_save_as, btn_cancel]
            mock_box.clickedButton.return_value = btn_overwrite
            mock_box_cls.return_value = mock_box

            result = win.action_save()
            self.assertTrue(result)
            win._engine.save.assert_called_once()
            self.assertFalse(win._is_modified)

        # Case 3: User chooses Save As -> redirects to action_save_as
        win._is_modified = True
        with patch("ui.main_window.QMessageBox") as mock_box_cls:
            mock_box = MagicMock()
            mock_box.addButton.side_effect = [btn_overwrite, btn_save_as, btn_cancel]
            mock_box.clickedButton.return_value = btn_save_as
            mock_box_cls.return_value = mock_box

            with patch.object(win, "action_save_as", return_value=True) as mock_save_as:
                result = win.action_save()
                self.assertTrue(result)
                mock_save_as.assert_called_once()

        # Case 4: Calling from QAction.triggered(False) still triggers warning (not bypassed by boolean arg)
        with patch("ui.main_window.QMessageBox") as mock_box_cls:
            mock_box = MagicMock()
            mock_box.addButton.side_effect = [btn_overwrite, btn_save_as, btn_cancel]
            mock_box.clickedButton.return_value = btn_cancel
            mock_box_cls.return_value = mock_box

            # Simulates Qt QAction triggered signal passing False
            result = win.action_save(False)
            self.assertFalse(result)
            mock_box.exec.assert_called_once()

    def test_double_click_english_word_detected_properties_preserved(self):
        """Verify double clicking English word opens dialog and retains detected features if not edited, or uses edited."""
        from unittest.mock import patch, MagicMock
        from ui.dialogs import MultiLineTextDialog
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        eng_block = TextBlock(
            page_index=0,
            rect=(120.0, 150.0, 200.0, 170.0),
            text="OriginalEnglish",
            font_name="Calibri",
            font_size=16.5,
            bold=True,
            italic=False,
            color="#2563eb",
        )
        self.engine.get_text_blocks = MagicMock(return_value=[eng_block])

        # Test double clicking near the word opens dialog
        page_item = self.view._page_items[0]
        scene_pos = page_item.pos() + QPointF(125.0, 155.0)
        view_pos = self.view.mapFromScene(scene_pos)

        dbl_ev = QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            QPointF(view_pos),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        with patch("ui.pdf_view.MultiLineTextDialog") as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = True
            mock_dlg.get_text.return_value = "ReplacementEnglish"
            mock_dlg_cls.return_value = mock_dlg

            with patch.object(self.engine, "redact_area") as mock_redact:
                self.view.mouseDoubleClickEvent(dbl_ev)
                mock_dlg_cls.assert_called_once()
                self.assertEqual(mock_dlg_cls.call_args.kwargs.get("initial_text"), "OriginalEnglish")

                # Verify properties were auto-detected and preserved without user modification
                mock_redact.assert_called_once()
                kwargs = mock_redact.call_args.kwargs
                self.assertEqual(kwargs.get("font_family"), "Calibri")
                self.assertEqual(kwargs.get("font_size"), 16.5)
                self.assertEqual(kwargs.get("color"), "#2563eb")
                self.assertEqual(kwargs.get("bold"), True)

    def test_bangla_word_extraction_merges_fragments(self):
        """Verify engine.get_text_blocks merges fragmented complex script words into whole words."""
        import tempfile
        import pymupdf
        from core.text_renderer import TextRenderer

        # Create a document with complex Bangla text
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "bangla_merge_test.pdf"
            doc = pymupdf.open()
            page = doc.new_page(width=595, height=842)
            renderer = TextRenderer()
            renderer.insert_text_to_page(
                page,
                (50, 50, 300, 100),
                "বাংলাদেশ আমি",
                font_family="Noto Sans Bengali",
                font_size=14.0,
            )
            doc.save(str(pdf_path))
            doc.close()

            eng = PdfEngine()
            eng.open(str(pdf_path))
            blocks = eng.get_text_blocks(0, level="word")
            extracted_words = [b.text for b in blocks]
            eng.close()

            # "বাংলাদেশ" must be a single merged whole word, not "বাংলাদ" and "েশ"
            self.assertTrue(any("বাংলাদেশ" in w for w in extracted_words), f"Extracted: {extracted_words}")
            self.assertTrue(any("আমি" in w for w in extracted_words), f"Extracted: {extracted_words}")

    def test_add_text_when_bangla_enabled_opens_editing_dialog(self):
        """When Bangla mode is enabled and user adds text with Tool.TEXT, open MultiLineTextDialog."""
        from core.bangla_input import BanglaPhoneticEngine
        from ui.dialogs import MultiLineTextDialog

        b_engine = BanglaPhoneticEngine()
        self.assertFalse(b_engine.is_active)
        self.assertFalse(b_engine.avro_phonetic_enabled)

        b_engine.set_active(True)
        self.assertTrue(b_engine.is_active)
        self.assertTrue(b_engine.avro_phonetic_enabled)

        # 1. Test MultiLineTextDialog with initial_bangla_mode=True
        dlg = MultiLineTextDialog(
            parent=None,
            title="Add Text",
            initial_text="",
            bangla_engine=b_engine,
            initial_bangla_mode=True,
        )
        self.assertIsNotNone(dlg._bangla_cb)
        self.assertTrue(dlg._bangla_cb.isChecked())
        self.assertFalse(dlg.preview_card.isHidden())

        # Simulate typing phonetic English 'amra shobai raja'
        dlg.text_edit.setPlainText("amra shobai raja")
        self.assertIn("আমরা সবাই রাজা", dlg.preview_label.text())
        self.assertEqual(dlg.get_text(), "আমরা সবাই রাজা")
        dlg.close()

        # 2. Test PdfView adding text when Bangla is enabled vs disabled
        view = PdfView()
        view.set_dependencies(self.engine, b_engine, None)
        view.load_document(self.engine)

        page_item = view._page_items[0]
        local_pt = QPointF(100.0, 150.0)

        # When Bangla is enabled: opens MultiLineTextDialog
        b_engine.set_active(True)
        with patch("ui.pdf_view.MultiLineTextDialog") as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = True
            mock_dlg.get_text.return_value = "আমরা সবাই রাজা"
            mock_dlg_cls.return_value = mock_dlg

            view.set_tool(Tool.TEXT)
            view._create_inline_text_dialog(0, page_item, local_pt)

            mock_dlg_cls.assert_called_once()
            _, kwargs = mock_dlg_cls.call_args
            self.assertTrue(kwargs.get("initial_bangla_mode"))

            # Check that text box was created with Bangla text and Bangla font
            added_item = list(view._overlay_items.values())[-1]
            self.assertEqual(added_item.data.text, "আমরা সবাই রাজা")
            self.assertEqual(added_item.data.font_family, "Noto Sans Bengali")
            self.assertEqual(view._current_tool, Tool.SELECT)

        # When Bangla is disabled: calls _start_inline_create_text (no dialog)
        b_engine.set_active(False)
        with patch.object(view, "_start_inline_create_text") as mock_inline:
            with patch("ui.pdf_view.MultiLineTextDialog") as mock_dlg_cls:
                view.set_tool(Tool.TEXT)
                view._create_inline_text_dialog(0, page_item, local_pt)
                mock_inline.assert_called_once_with(0, page_item, local_pt)
                mock_dlg_cls.assert_not_called()

    def test_inline_english_backspace_and_avro_dialog_typing(self):
        """Verify backspace works in English inline text editor and Avro dialog allows full typing."""
        from core.bangla_input import BanglaPhoneticEngine
        from ui.dialogs import MultiLineTextDialog
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent

        # 1. Test Backspace in English inline text editor via view.keyPressEvent
        view = PdfView()
        view.set_dependencies(self.engine, None, None)
        view.load_document(self.engine)
        page_item = view._page_items[0]

        view._start_inline_create_text(0, page_item, QPointF(50.0, 50.0))
        proxies = [it for it in view._scene.items() if hasattr(it, "widget") and isinstance(it.widget(), InlineCanvasTextEditor)]
        self.assertEqual(len(proxies), 1)
        editor = proxies[0].widget()
        editor.setText("Hello")
        editor.setCursorPosition(5)

        # Send Backspace key event to view
        bs_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        view.keyPressEvent(bs_ev)
        self.assertEqual(editor.text(), "Hell")

        bs_ev2 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        view.keyPressEvent(bs_ev2)
        self.assertEqual(editor.text(), "Hel")

        # 2. Test Avro dialog typing when Bangla engine is active
        b_engine = BanglaPhoneticEngine()
        b_engine.set_active(True)
        self.app.installEventFilter(b_engine)

        dlg = MultiLineTextDialog(title="Add Text", initial_text="", bangla_engine=b_engine, initial_bangla_mode=True)
        dlg.show()
        self.app.processEvents()

        # Check native QWindow events are NOT blocked
        win_handle = dlg.windowHandle()
        if win_handle:
            key_ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
            self.assertFalse(b_engine.eventFilter(win_handle, key_ev))

        # Check typing directly into text_edit
        self.assertTrue(dlg.text_edit.isEnabled())
        self.assertFalse(dlg.text_edit.isReadOnly())
        dlg.text_edit.setPlainText("bangla")
        self.assertEqual(dlg.preview_label.text(), "বাংলা")
        self.assertEqual(dlg.get_text(), "বাংলা")

        # Check Backspace in text_edit
        dlg.text_edit.setPlainText("bangl")
        self.assertEqual(dlg.get_text(), "বাংল")
        dlg.close()

    def tearDown(self):
        self.engine.close()


if __name__ == "__main__":
    unittest.main()
