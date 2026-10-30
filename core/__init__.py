"""
Core package for the offline PDF editor with Bangla support.

Provides the main engine, text rendering, Bangla phonetic input,
annotation management, page manipulation tools, and undo/redo system.
"""

from core.pdf_engine import PdfEngine
from core.text_renderer import TextRenderer
from core.bangla_input import BanglaPhoneticEngine
from core.annotations import AnnotationManager
from core.page_tools import PageTools
from core.undo_redo import UndoStack, Command

__all__ = [
    "PdfEngine",
    "TextRenderer",
    "BanglaPhoneticEngine",
    "AnnotationManager",
    "PageTools",
    "UndoStack",
    "Command",
]
