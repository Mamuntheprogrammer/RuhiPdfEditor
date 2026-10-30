"""
Internationalization (i18n) module for PDF Editor.

Supports dynamic switching between English and Bangla (বাংলা).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported UI languages."""
    ENGLISH = "en"
    BANGLA = "bn"


class I18n(QObject):
    """Internationalization manager for the application."""

    language_changed = Signal(Language)

    STRINGS: dict[Language, dict[str, str]] = {
        Language.ENGLISH: {
            # Application
            "app_title": "PDF Editor (Bangla Supported)",
            "untitled": "Untitled",
            "version": "Version {ver}",
            "ready": "Ready",
            "about": "About PDF Editor",
            "about_description": "A simple, fully offline desktop PDF editor with proper HarfBuzz-shaped Bangla support.",
            "credits": "Credits",
            "font": "Font",
            "text_shaping": "Complex Text Shaping Engine",
            "license_info": "Free and Open Source under the MIT License.",

            # Menus
            "menu_file": "&File",
            "menu_edit": "&Edit",
            "menu_view": "&View",
            "menu_tools": "&Tools",
            "menu_pages": "&Pages",
            "menu_language": "&Language",
            "menu_help": "&Help",

            # Actions & Tools
            "open_file": "Open PDF",
            "save_file": "Save",
            "save_as": "Save As...",
            "export_as_image": "Export Page as Image...",
            "close": "Close",
            "exit": "Exit",
            "undo": "Undo",
            "redo": "Redo",
            "action_delete": "Delete Selected (Del)",
            "zoom_in": "Zoom In",
            "zoom_out": "Zoom Out",
            "zoom_fit": "Fit to Width",
            "zoom_actual_size": "Actual Size (100%)",
            "zoom_fit_page": "Fit Page",
            "zoom_fit_width": "Fit to Width",
            "zoom_fit_height": "Fit to Height",
            "read_mode": "Read Mode",
            "exit_read_mode": "Exit Read Mode",
            "full_screen": "Full Screen",
            "theme_light": "Light Theme",
            "theme_dark": "Dark Theme",
            "toggle_bangla": "Toggle Bangla Input (Ctrl+Space)",
            "lang_english": "English",
            "lang_bangla": "বাংলা (Bangla)",

            # Tool names & tooltips
            "tool_select": "Select / Move (V)",
            "tool_text": "Add Text (T)",
            "tool_highlight": "Highlight Text",
            "tool_underline": "Underline Text",
            "tool_strikethrough": "Strikethrough Text",
            "tool_rectangle": "Rectangle Shape",
            "tool_line": "Straight Line",
            "tool_arrow": "Arrow",
            "tool_pen": "Freehand Pen",
            "tool_image": "Insert Image",
            "tool_signature": "Insert Signature",
            "tool_eraser": "Erase / Redact Text (E)",
            "tool_redact": "Redact / Replace Text",

            # Properties panel
            "properties": "Properties",
            "font_family": "Font Family:",
            "font_size": "Font Size:",
            "decrease_font_size": "Decrease Font Size",
            "increase_font_size": "Increase Font Size",
            "text_color": "Text Color:",
            "bold": "Bold",
            "italic": "Italic",
            "stroke_color": "Stroke Color:",
            "fill_color": "Fill Color:",
            "stroke_width": "Stroke Width:",
            "opacity": "Opacity:",
            "color": "Color:",

            # Pages & Thumbnails
            "pages": "Pages",
            "page": "Page",
            "page_selection": "Page Selection",
            "current_page_num": "Current Page ({page})",
            "all_pages": "All Pages",
            "page_range": "Page Range:",
            "delete_page": "Delete Page",
            "rotate_page": "Rotate 90° Clockwise",
            "insert_blank_page": "Insert Blank Page",
            "page_ranges": "Page Ranges",

            # Dialogs
            "merge_pdfs": "Merge PDFs",
            "merge_instructions": "Add PDF files in the desired order and click Merge:",
            "split_pdf": "Split PDF",
            "split_info": "Document has {pages} pages.",
            "split_range_hint": "Enter page ranges (e.g., 1-3, 5, 7-10):",
            "output_directory": "Output Directory:",
            "settings": "Settings",
            "format": "Image Format:",
            "add": "Add Files...",
            "remove": "Remove",
            "move_up": "Move Up",
            "move_down": "Move Down",
            "browse": "Browse...",
            "ok": "OK",
            "cancel": "Cancel",
            "confirm": "Confirm",
            "warning": "Warning",
            "error": "Error",
            "select_pdf_files": "Select PDF Files",
            "select_output_directory": "Select Output Directory",
            "select_image_file": "Select Image File",
            "invalid_range": "Invalid Page Range",
            "split_range_error": "Please enter a valid page range specification.",
            "no_directory": "No Directory Selected",
            "confirm_delete_page": "Are you sure you want to delete this page?",
            "confirm_unsaved_changes": "You have unsaved changes. Do you want to save before closing?",

            # Status bar
            "status_page_info": "Page: {current} / {total}",
            "status_zoom": "Zoom: {zoom}%",
            "status_bangla_on": "Bangla [Avro]: ON",
            "status_bangla_off": "Bangla [Avro]: OFF",
            "saved_successfully": "Saved successfully: {path}",
            "exported_successfully": "Exported successfully: {path}",
        },

        Language.BANGLA: {
            # Application
            "app_title": "পিডিএফ সম্পাদক (বাংলা সমর্থিত)",
            "untitled": "শিরোনামহীন",
            "version": "সংস্করণ {ver}",
            "ready": "প্রস্তুত",
            "about": "পিডিএফ সম্পাদক পরিচিতি",
            "about_description": "হার্ফবাজ সমর্থিত সঠিক বাংলাযুক্ত সহজ, সম্পূর্ণ অফলাইন ডেস্কটপ পিডিএফ সম্পাদক।",
            "credits": "কৃতজ্ঞতা",
            "font": "ফন্ট",
            "text_shaping": "জটিল লিপি রূপান্তর ইঞ্জিন",
            "license_info": "এমআইটি লাইসেন্সের অধীনে উন্মুক্ত ও ফ্রি।",

            # Menus
            "menu_file": "&ফাইল",
            "menu_edit": "&সম্পাদনা",
            "menu_view": "&প্রদর্শন",
            "menu_tools": "&টুলস",
            "menu_pages": "&পৃষ্ঠাসমূহ",
            "menu_language": "&ভাষা",
            "menu_help": "&সাহায্য",

            # Actions & Tools
            "open_file": "পিডিএফ খুলুন",
            "save_file": "সংরক্ষণ",
            "save_as": "নতুন নামে সংরক্ষণ...",
            "export_as_image": "ছবি হিসেবে রপ্তানি...",
            "close": "বন্ধ করুন",
            "exit": "প্রস্থান",
            "undo": "পূর্বাবস্থা (আনডু)",
            "redo": "পুনরাবৃত্তি (রিডু)",
            "action_delete": "নির্বাচিত উপাদান মুছুন (Del)",
            "zoom_in": "বড় করুন",
            "zoom_out": "ছোট করুন",
            "zoom_fit": "প্রস্থে মানানসই",
            "zoom_actual_size": "প্রকৃত আকার (১০০%)",
            "zoom_fit_page": "পুরো পৃষ্ঠা ফিট",
            "zoom_fit_width": "প্রস্থে মানানসই",
            "zoom_fit_height": "উচ্চতায় মানানসই",
            "read_mode": "পঠন মোড (রিড মোড)",
            "exit_read_mode": "পঠন মোড ত্যাগ করুন",
            "full_screen": "সম্পূর্ণ পর্দা (ফুল স্ক্রিন)",
            "theme_light": "হালকা থিম",
            "theme_dark": "গাঢ় থিম",
            "toggle_bangla": "বাংলা ইনপুট টগল (Ctrl+Space)",
            "lang_english": "English",
            "lang_bangla": "বাংলা (Bangla)",

            # Tool names & tooltips
            "tool_select": "নির্বাচন / স্থানান্তর (V)",
            "tool_text": "লেখা যোগ করুন (T)",
            "tool_highlight": "হাইলাইট করুন",
            "tool_underline": "আন্ডারলাইন করুন",
            "tool_strikethrough": "স্ট্রাইক-থ্রু করুন",
            "tool_rectangle": "আয়তক্ষেত্র",
            "tool_line": "সরলরেখা",
            "tool_arrow": "তীরচিহ্ন",
            "tool_pen": "কলম (ফ্রিহ্যান্ড)",
            "tool_image": "ছবি সংযুক্ত করুন",
            "tool_signature": "স্বাক্ষর সংযুক্ত করুন",
            "tool_eraser": "লেখা মুছে ফেলা / ইরেজার (E)",
            "tool_redact": "লেখা ঢেকে প্রতিস্থাপন",

            # Properties panel
            "properties": "বৈশিষ্ট্যাবলী",
            "font_family": "ফন্ট পরিবার:",
            "font_size": "ফন্টের আকার:",
            "decrease_font_size": "ফন্টের আকার কমান",
            "increase_font_size": "ফন্টের আকার বাড়ান",
            "text_color": "লেখার রঙ:",
            "bold": "বোল্ড (গাঢ়)",
            "italic": "ইটালিক (বাঁকা)",
            "stroke_color": "রেখার রঙ:",
            "fill_color": "ভরাটের রঙ:",
            "stroke_width": "রেখার পুরুত্ব:",
            "opacity": "স্বচ্ছতা:",
            "color": "রঙ:",

            # Pages & Thumbnails
            "pages": "পৃষ্ঠাসমূহ",
            "page": "পৃষ্ঠা",
            "page_selection": "পৃষ্ঠা নির্বাচন",
            "current_page_num": "বর্তমান পৃষ্ঠা ({page})",
            "all_pages": "সব পৃষ্ঠা",
            "page_range": "পৃষ্ঠা পরিসীমা:",
            "delete_page": "পৃষ্ঠা মুছুন",
            "rotate_page": "ডানে ঘোরান (৯০°)",
            "insert_blank_page": "খালি পৃষ্ঠা যোগ করুন",
            "page_ranges": "পৃষ্ঠা পরিসীমা",

            # Dialogs
            "merge_pdfs": "পিডিএফ একত্রীকরণ (Merge)",
            "merge_instructions": "প্রয়োজনীয় ক্রমানুসারে পিডিএফ ফাইল যোগ করে একত্র করুন:",
            "split_pdf": "পিডিএফ বিভাজন (Split)",
            "split_info": "নথিতে মোট {pages} টি পৃষ্ঠা আছে।",
            "split_range_hint": "পৃষ্ঠা পরিসীমা লিখুন (যেমন: ১-৩, ৫, ৭-১০):",
            "output_directory": "ফলাফল ফোল্ডার:",
            "settings": "সেটিংস",
            "format": "ছবির ফরম্যাট:",
            "add": "ফাইল যোগ করুন...",
            "remove": "মুছুন",
            "move_up": "উপরে নিন",
            "move_down": "নিচে নিন",
            "browse": "ব্রাউজ...",
            "ok": "ঠিক আছে",
            "cancel": "বাতিল",
            "confirm": "নিশ্চিতকরণ",
            "warning": "সতর্কতা",
            "error": "ত্রুটি",
            "select_pdf_files": "পিডিএফ ফাইল নির্বাচন করুন",
            "select_output_directory": "ফোল্ডার নির্বাচন করুন",
            "select_image_file": "ছবির ফাইল নির্বাচন করুন",
            "invalid_range": "ভুল পৃষ্ঠা পরিসীমা",
            "split_range_error": "দয়া করে সঠিক পৃষ্ঠা পরিসীমা প্রদান করুন।",
            "no_directory": "কোনো ফোল্ডার নির্বাচিত হয়নি",
            "confirm_delete_page": "আপনি কি নিশ্চিত এই পৃষ্ঠাটি মুছে ফেলতে চান?",
            "confirm_unsaved_changes": "অসংরক্ষিত পরিবর্তন রয়েছে। বন্ধ করার আগে কি সংরক্ষণ করতে চান?",

            # Status bar
            "status_page_info": "পৃষ্ঠা: {current} / {total}",
            "status_zoom": "জুম: {zoom}%",
            "status_bangla_on": "বাংলা [অভ্র]: চালু",
            "status_bangla_off": "বাংলা [অভ্র]: বন্ধ",
            "saved_successfully": "সফলভাবে সংরক্ষিত হয়েছে: {path}",
            "exported_successfully": "সফলভাবে ছবি রপ্তানি হয়েছে: {path}",
        },
    }

    def __init__(self, language: Language = Language.ENGLISH) -> None:
        super().__init__()
        self._language: Language = language

    @property
    def language(self) -> Language:
        return self._language

    def set_language(self, language: Language) -> None:
        if self._language != language:
            self._language = language
            logger.info("Language changed to: %s", language.value)
            self.language_changed.emit(self._language)

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate key for current language with fallback to English then key."""
        table = self.STRINGS.get(self._language, {})
        val = table.get(key)
        if val is None:
            # Fallback to English
            val = self.STRINGS[Language.ENGLISH].get(key, key)

        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

    def tr(self, key: str, **kwargs: Any) -> str:
        """Alias for t()."""
        return self.t(key, **kwargs)

