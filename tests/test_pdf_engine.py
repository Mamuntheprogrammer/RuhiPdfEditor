"""Tests for the PDF engine core functionality."""
import unittest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPdfEngine(unittest.TestCase):
    """Test PdfEngine basic operations."""
    
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        from core.pdf_engine import PdfEngine
        self.engine = PdfEngine()
        self.test_dir = Path(tempfile.mkdtemp())
    
    def test_create_new(self):
        """Test creating a new empty PDF."""
        self.engine.create_new()
        self.assertIsNotNone(self.engine.document)
        self.assertEqual(self.engine.page_count, 1)
    
    def test_save_and_open(self):
        """Test save and reopen cycle."""
        self.engine.create_new()
        save_path = str(self.test_dir / "test.pdf")
        self.engine.save(save_path)
        self.assertTrue(os.path.exists(save_path))
        
        self.engine.close()
        self.engine.open(save_path)
        self.assertEqual(self.engine.page_count, 1)
    
    def test_render_page(self):
        """Test page rendering to QPixmap."""
        self.engine.create_new()
        pixmap = self.engine.render_page(0)
        self.assertFalse(pixmap.isNull())
    
    def test_page_size(self):
        """Test getting page dimensions."""
        self.engine.create_new()
        w, h = self.engine.get_page_size(0)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
    
    def tearDown(self):
        self.engine.close()
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


class TestPageTools(unittest.TestCase):
    """Test page manipulation tools."""
    
    def setUp(self):
        import fitz
        self.doc = fitz.open()
        for i in range(5):
            self.doc.new_page()
        self.test_dir = Path(tempfile.mkdtemp())
    
    def test_delete_page(self):
        from core.page_tools import PageTools
        initial_count = self.doc.page_count
        PageTools.delete_page(self.doc, 0)
        self.assertEqual(self.doc.page_count, initial_count - 1)
    
    def test_rotate_page(self):
        from core.page_tools import PageTools
        PageTools.rotate_page(self.doc, 0, 90)
        self.assertEqual(self.doc[0].rotation, 90)
    
    def test_merge_pdfs(self):
        import fitz
        from core.page_tools import PageTools
        
        # Create two test PDFs
        doc1_path = str(self.test_dir / "doc1.pdf")
        doc2_path = str(self.test_dir / "doc2.pdf")
        output_path = str(self.test_dir / "merged.pdf")
        
        doc1 = fitz.open()
        doc1.new_page()
        doc1.new_page()
        doc1.save(doc1_path)
        doc1.close()
        
        doc2 = fitz.open()
        doc2.new_page()
        doc2.save(doc2_path)
        doc2.close()
        
        PageTools.merge_pdfs([doc1_path, doc2_path], output_path)
        
        merged = fitz.open(output_path)
        self.assertEqual(merged.page_count, 3)
        merged.close()
    
    def test_split_pdf(self):
        import fitz
        from core.page_tools import PageTools
        
        output_dir = str(self.test_dir / "split_output")
        os.makedirs(output_dir, exist_ok=True)
        
        result = PageTools.split_pdf(self.doc, [(0, 1), (2, 4)], output_dir)
        self.assertEqual(len(result), 2)
        for path in result:
            self.assertTrue(os.path.exists(path))
    
    def tearDown(self):
        self.doc.close()
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


class TestUndoRedo(unittest.TestCase):
    """Test undo/redo system."""
    
    def test_push_and_undo(self):
        from core.undo_redo import UndoStack, Command
        
        class TestCommand(Command):
            def __init__(self):
                self.executed = False
            def execute(self):
                self.executed = True
            def undo(self):
                self.executed = False
        
        stack = UndoStack()
        cmd = TestCommand()
        stack.push(cmd)
        self.assertTrue(cmd.executed)
        self.assertTrue(stack.can_undo)
        
        stack.undo()
        self.assertFalse(cmd.executed)
        self.assertTrue(stack.can_redo)
        
        stack.redo()
        self.assertTrue(cmd.executed)


if __name__ == "__main__":
    unittest.main()
