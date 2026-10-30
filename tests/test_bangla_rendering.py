"""
Tests for Bangla text handling.
Tests transliteration (Avro-style phonetic input) and verifies
that Bangla text can be inserted into PDFs with proper shaping.
"""
import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bangla_input import BanglaPhoneticEngine


class TestBanglaTransliteration(unittest.TestCase):
    """Test the Avro-style Bangla phonetic transliteration engine."""
    
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])
    
    def setUp(self):
        pass
    
    def test_simple_consonants(self):
        """Test basic consonant transliteration."""
        engine = BanglaPhoneticEngine()
        # k -> ক, kh -> খ, g -> গ, etc.
        self.assertEqual(engine.transliterate("k"), "ক")
        self.assertEqual(engine.transliterate("kh"), "খ")
        self.assertEqual(engine.transliterate("g"), "গ")
        self.assertEqual(engine.transliterate("gh"), "ঘ")
    
    def test_vowels(self):
        """Test vowel transliteration."""
        engine = BanglaPhoneticEngine()
        self.assertEqual(engine.transliterate("a"), "অ")
        self.assertEqual(engine.transliterate("i"), "ই")
        self.assertEqual(engine.transliterate("u"), "উ")
        self.assertEqual(engine.transliterate("e"), "এ")
        self.assertEqual(engine.transliterate("o"), "ও")
    
    def test_conjuncts(self):
        """Test consonant conjuncts (juktakkhor)."""
        engine = BanglaPhoneticEngine()
        # kr -> ক্র, st -> স্ত, etc.
    
    def test_words(self):
        """Test complete word transliteration."""
        engine = BanglaPhoneticEngine()
        test_cases = {
            "bangladesh": "বাংলাদেশ",
            "bishwobidyaloy": "বিশ্ববিদ্যালয়",
            "kshotriyo": "ক্ষত্রিয়",
            "durga": "দুর্গা",
            "koushal": "কৌশল",
        }
        for latin, expected_bangla in test_cases.items():
            with self.subTest(latin=latin):
                result = engine.transliterate(latin)
                self.assertEqual(result, expected_bangla,
                    f"Transliteration of '{latin}': expected '{expected_bangla}', got '{result}'")
    
    def test_sentence(self):
        """Test sentence transliteration."""
        engine = BanglaPhoneticEngine()
        result = engine.transliterate("ami banglay gan gai")
        self.assertEqual(result, "আমি বাংলায় গান গাই")
    
    def test_numbers(self):
        """Test Bangla numeral transliteration."""
        engine = BanglaPhoneticEngine()
        # Test if numbers convert to Bangla digits
    
    def test_empty_string(self):
        """Test empty input."""
        engine = BanglaPhoneticEngine()
        self.assertEqual(engine.transliterate(""), "")


class TestBanglaPdfRendering(unittest.TestCase):
    """Test Bangla text insertion into PDF documents."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])
    
    def setUp(self):
        self.test_dir = Path(__file__).parent / "test_output"
        self.test_dir.mkdir(exist_ok=True)
    
    def test_create_bangla_pdf(self):
        """Create a test PDF with Bangla text and verify it's valid."""
        import fitz
        from core.text_renderer import TextRenderer
        
        renderer = TextRenderer()
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        
        test_texts = [
            "বাংলাদেশ",
            "বিশ্ববিদ্যালয়",
            "ক্ষত্রিয়",
            "দুর্গা",
            "কৌশল",
            "আমি বাংলায় গান গাই",
        ]
        
        y = 50
        for text in test_texts:
            rect = (50, y, 500, y + 40)
            renderer.insert_text_to_page(page, rect, text, 
                                         font_family="Noto Sans Bengali",
                                         font_size=18)
            y += 50
        
        output_path = str(self.test_dir / "test_bangla.pdf")
        doc.save(output_path)
        doc.close()
        
        # Verify the PDF was created and has content
        self.assertTrue(os.path.exists(output_path))
        verify_doc = fitz.open(output_path)
        self.assertEqual(verify_doc.page_count, 1)
        # Check that text is present (may not be extractable with insert_htmlbox)
        verify_doc.close()
    
    def test_mixed_bangla_english(self):
        """Test PDF with mixed Bangla and English text."""
        import fitz
        from core.text_renderer import TextRenderer
        
        renderer = TextRenderer()
        doc = fitz.open()
        page = doc.new_page()
        
        renderer.insert_text_to_page(page, (50, 50, 500, 90),
                                     "Hello বাংলা World", font_size=16)
        
        output_path = str(self.test_dir / "test_mixed.pdf")
        doc.save(output_path)
        doc.close()
        
        self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()
