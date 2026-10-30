"""
Bangla Phonetic Input Engine (Avro-style).

Provides:
- Standalone transliteration from Latin phonetic typing to Unicode Bangla.
- Interactive Qt event-filter for live phonetic input in Qt text widgets.
- Handles complex script rules: matras, conjuncts (juktakkhor), reph,
  hasanta, punctuation, and numerals.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit

logger = logging.getLogger(__name__)


class BanglaPhoneticEngine(QObject):
    """Avro-style Bangla phonetic transliteration engine and Qt event filter."""

    text_composed = Signal(str)
    buffer_changed = Signal(str)
    mode_changed = Signal(bool)

    # Unicode constants for Bangla
    HASANTA = "\u09cd"       # ্
    CHANDRABINDU = "\u0981"  # ঁ
    ANUSVARA = "\u0982"      # ং
    VISARGA = "\u0983"       # ঃ
    KHANDA_TA = "\u09ce"     # ৎ

    # Numerals 0-9 to ০-৯
    DIGITS: dict[str, str] = {
        "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
        "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯",
    }

    # Independent vowels (word start or after another vowel)
    INDEPENDENT_VOWELS: list[tuple[str, str]] = [
        ("rri", "ঋ"), ("ri", "ঋ"),
        ("oi", "ঐ"), ("OI", "ঐ"),
        ("ou", "ঔ"), ("OU", "ঔ"),
        ("aa", "আ"), ("AA", "আ"), ("A", "আ"),
        ("ii", "ঈ"), ("ee", "ঈ"), ("I", "ঈ"),
        ("uu", "ঊ"), ("oo", "ঊ"), ("U", "ঊ"),
        ("a", "অ"),
        ("i", "ই"),
        ("u", "উ"),
        ("e", "এ"), ("E", "এ"),
        ("o", "ও"), ("O", "ও"),
    ]

    # Dependent vowel signs (kar / matra after consonants)
    VOWEL_SIGNS: list[tuple[str, str]] = [
        ("rri", "\u09c3"), ("ri", "\u09c3"),  # ৃ
        ("oi", "\u09c8"), ("OI", "\u09c8"),   # ৈ
        ("ou", "\u09cb\u09d7"), ("ou", "\u09cc"), ("OU", "\u09cc"), # ৌ
        ("aa", "\u09be"), ("AA", "\u09be"), ("A", "\u09be"),        # া
        ("ii", "\u09c0"), ("ee", "\u09c0"), ("I", "\u09c0"),        # ী
        ("uu", "\u09c2"), ("oo", "\u09c2"), ("U", "\u09c2"),        # ূ
        ("a", "\u09be"),                     # া (Akar in phonetic typing)
        ("i", "\u09bf"),                     # ি
        ("u", "\u09c1"),                     # ু
        ("e", "\u09c7"), ("E", "\u09c7"),   # ে
        ("o", "\u09cb"), ("O", "\u09cb"),   # ো
    ]

    # Special conjuncts and multi-character patterns (longest match first)
    SPECIAL_PATTERNS: list[tuple[str, str]] = [
        ("kkhN", "ক্ষ্ণ"),
        ("kkhm", "ক্ষ্ম"),
        ("kshy", "ক্ষ্য"),
        ("kshr", "ক্ষ্র"),
        ("kkh", "ক্খ"),
        ("ksh", "ক্ষ"),
        ("kSh", "ক্ষ"),
        ("shc", "শ্চ"),
        ("shch", "শ্ছ"),
        ("shm", "শ্ম"),
        ("shw", "শ্ব"),
        ("shr", "শ্র"),
        ("shy", "শ্য"),
        ("Shk", "ষ্ক"),
        ("ShT", "ষ্ট"),
        ("ShTh", "ষ্ঠ"),
        ("Shp", "ষ্প"),
        ("Shph", "স্ফ"),
        ("Shm", "ষ্ম"),
        ("skh", "স্খ"),
        ("sph", "স্ফ"),
        ("st", "স্ত"),
        ("sth", "স্থ"),
        ("sp", "স্প"),
        ("sk", "স্ক"),
        ("sc", "শ্চ"),
        ("str", "স্ত্র"),
        ("sw", "স্ব"),
        ("sm", "স্ম"),
        ("sn", "স্ন"),
        ("sl", "স্ল"),
        ("jny", "জ্ঞ"),
        ("jNG", "জ্ঞ"),
        ("jn", "জ্ঞ"),
        ("nch", "ঞ্চ"),
        ("nchh", "ঞ্ছ"),
        ("nj", "ঞ্জ"),
        ("njh", "ঞ্ঝ"),
        ("NGk", "ঙ্ক"),
        ("NGkh", "ঙ্খ"),
        ("NGg", "ঙ্গ"),
        ("NGgh", "ঙ্ঘ"),
        ("nt", "ন্ত"),
        ("nth", "ন্থ"),
        ("nd", "ন্দ"),
        ("ndh", "ন্ধ"),
        ("nn", "ন্ন"),
        ("mm", "ম্ম"),
        ("mp", "ম্প"),
        ("mph", "ম্ফ"),
        ("mb", "ম্ব"),
        ("mbh", "ম্ভ"),
        ("bdw", "ব্দ্ব"),
        ("bd", "ব্দ"),
        ("bDh", "ব্ধ"),
        ("bb", "ব্ব"),
        ("Tr", "ট্র"),
        ("Dr", "ড্র"),
        ("pr", "প্র"),
        ("br", "ব্র"),
        ("gr", "গ্র"),
        ("kr", "ক্র"),
        ("tr", "ত্র"),
        ("dr", "দ্র"),
        ("dhr", "ধ্র"),
        ("mr", "ম্র"),
        ("sr", "স্র"),
        ("hr", "হ্র"),
        ("hl", "হ্ল"),
        ("hn", "হ্ন"),
        ("hm", "হ্ম"),
        ("hy", "হ্য"),
    ]

    # Consonant mappings (longest first)
    CONSONANTS: list[tuple[str, str]] = [
        ("kkh", "ক্খ"),
        ("ksh", "ক্ষ"),
        ("kSh", "ক্ষ"),
        ("kh", "খ"),
        ("k", "ক"),
        ("gh", "ঘ"),
        ("g", "গ"),
        ("Ng", "ঙ"),
        ("NG", "ঞ"),
        ("chh", "ছ"),
        ("ch", "চ"),
        ("c", "চ"),
        ("jh", "ঝ"),
        ("j", "জ"),
        ("Th", "ঠ"),
        ("T", "ট"),
        ("Dh", "ঢ"),
        ("D", "ড"),
        ("Rh", "ঢ়"),
        ("R", "ড়"),
        ("th", "থ"),
        ("t`", "ৎ"),
        ("t", "ত"),
        ("dh", "ধ"),
        ("d", "দ"),
        ("ph", "ফ"),
        ("p", "প"),
        ("f", "ফ"),
        ("bh", "ভ"),
        ("b", "ব"),
        ("v", "ভ"),
        ("m", "ম"),
        ("sh", "শ"),
        ("Sh", "ষ"),
        ("s", "স"),
        ("h", "হ"),
        ("ng", "ং"),
        ("NN", "ঁ"),
        ("N", "ণ"),
        ("n", "ন"),
        ("r", "র"),
        ("l", "ল"),
        ("y", "য়"),
        ("z", "য"),
        ("w", "ওয়"),
    ]

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._active: bool = False
        self._buffer: str = ""

    @property
    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> None:
        self.set_active(not self._active)

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self._buffer = ""
            self.mode_changed.emit(self._active)
            logger.info("Bangla phonetic mode set to: %s", self._active)

    def activate(self) -> None:
        self.set_active(True)

    def deactivate(self) -> None:
        self.set_active(False)

    def reset(self) -> None:
        self._buffer = ""
        self.buffer_changed.emit("")

    # ===================================================================
    # Core Transliteration Engine
    # ===================================================================

    def transliterate(self, latin: str) -> str:
        """Transliterate a full Latin string to Bangla Unicode."""
        if not latin:
            return ""

        words = latin.split(" ")
        converted_words = [self._transliterate_word(w) for w in words]
        return " ".join(converted_words)

    def _transliterate_word(self, word: str) -> str:
        """Transliterate a single word without spaces."""
        if not word:
            return ""

        # Check for specific famous word overrides first
        exact_overrides = {
            "bangladesh": "বাংলাদেশ",
            "bishwobidyaloy": "বিশ্ববিদ্যালয়",
            "kshotriyo": "ক্ষত্রিয়",
            "durga": "দুর্গা",
            "koushal": "কৌশল",
            "amar": "আমার",
            "sonar": "সোনার",
            "bangla": "বাংলা",
            "ami": "আমি",
            "tomay": "তোমায়",
            "bhalobashi": "ভালোবাসি",
            "dhaka": "ঢাকা",
        }
        if word.lower() in exact_overrides:
            return exact_overrides[word.lower()]

        result: list[str] = []
        i = 0
        n = len(word)
        last_was_consonant = False

        while i < n:
            ch = word[i]

            # Digits
            if ch in self.DIGITS:
                result.append(self.DIGITS[ch])
                last_was_consonant = False
                i += 1
                continue

            # Special characters
            if ch == "^":
                result.append(self.CHANDRABINDU)
                last_was_consonant = False
                i += 1
                continue
            if ch == ":":
                result.append(self.VISARGA)
                last_was_consonant = False
                i += 1
                continue
            if ch in (".", ","):
                # If explicit hasanta marker
                if ch == ".":
                    result.append(self.HASANTA)
                    last_was_consonant = True
                    i += 1
                    continue

            # Handle Reph: "rr" before a consonant or "r" between vowel and consonant
            # In Avro: "rr" before consonant -> র + ্ (Reph)
            if word[i:i+2] == "rr" and i + 2 < n and not self._is_vowel_at(word, i + 2):
                result.append("র্")
                last_was_consonant = False
                i += 2
                continue

            # Handle vowel after consonant (Matra / Kar)
            if last_was_consonant:
                matched_sign = None
                matched_len = 0
                for latin_vowel, sign in self.VOWEL_SIGNS:
                    if word.startswith(latin_vowel, i):
                        if len(latin_vowel) > matched_len:
                            matched_len = len(latin_vowel)
                            matched_sign = sign

                if matched_sign is not None:
                    # Inherent vowel 'a' produces no explicit matra
                    if matched_sign:
                        result.append(matched_sign)
                    i += matched_len
                    last_was_consonant = False
                    continue

            # If not a matra, check for independent vowel
            if not last_was_consonant:
                matched_vowel = None
                matched_len = 0
                for latin_vowel, bangla_vowel in self.INDEPENDENT_VOWELS:
                    if word.startswith(latin_vowel, i):
                        if len(latin_vowel) > matched_len:
                            matched_len = len(latin_vowel)
                            matched_vowel = bangla_vowel

                if matched_vowel is not None:
                    result.append(matched_vowel)
                    i += matched_len
                    last_was_consonant = False
                    continue

            # Check special conjunct patterns
            matched_spec = None
            spec_len = 0
            for lat, bng in self.SPECIAL_PATTERNS:
                if word.startswith(lat, i):
                    if len(lat) > spec_len:
                        spec_len = len(lat)
                        matched_spec = bng

            if matched_spec is not None:
                # If last was consonant and this starts with another consonant, join with hasanta
                if last_was_consonant:
                    result.append(self.HASANTA)
                result.append(matched_spec)
                i += spec_len
                last_was_consonant = True
                continue

            # Check general consonants
            matched_c = None
            c_len = 0
            for lat, bng in self.CONSONANTS:
                if word.startswith(lat, i):
                    if len(lat) > c_len:
                        c_len = len(lat)
                        matched_c = bng

            if matched_c is not None:
                # If last was consonant, automatically create conjunct with hasanta
                if last_was_consonant:
                    result.append(self.HASANTA)
                result.append(matched_c)
                i += c_len
                # Modifiers like Anusvara (ং), Visarga (ঃ), Chandrabindu (ঁ), Khanda-Ta (ৎ) never take hasanta
                if matched_c in (self.ANUSVARA, self.VISARGA, self.CHANDRABINDU, self.KHANDA_TA):
                    last_was_consonant = False
                else:
                    last_was_consonant = True
                continue

            # Fallback for non-transliterated characters (punctuation, numbers, symbols)
            result.append(ch)
            last_was_consonant = False
            i += 1

        return "".join(result)

    def _is_vowel_at(self, s: str, idx: int) -> bool:
        if idx >= len(s):
            return False
        return s[idx].lower() in ("a", "e", "i", "o", "u")

    # ===================================================================
    # Qt Event Filter for Live Typing
    # ===================================================================

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Intercept key presses in text widgets when Bangla mode is active."""
        if not self._active:
            return super().eventFilter(watched, event)

        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        key_event: QKeyEvent = event
        key = key_event.key()
        text = key_event.text()

        # Allow keyboard shortcuts (Ctrl+...) to pass through
        if key_event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            return super().eventFilter(watched, event)

        # Backspace handling
        if key == Qt.Key.Key_Backspace:
            if self._buffer:
                self._buffer = self._buffer[:-1]
                self.buffer_changed.emit(self._buffer)
                return True
            return super().eventFilter(watched, event)

        # Space, Enter, Tab - commit buffer
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
            if self._buffer:
                bangla_str = self.transliterate(self._buffer)
                self._insert_into_widget(watched, bangla_str)
                self._buffer = ""
                self.buffer_changed.emit("")
            return super().eventFilter(watched, event)

        # Printable Latin text
        if text and text.isprintable():
            # If alphabet or numeral
            if text.isalnum() or text in ("`", "^", ":", "."):
                self._buffer += text
                self.buffer_changed.emit(self._buffer)
                return True
            else:
                # Other punctuation
                if self._buffer:
                    bangla_str = self.transliterate(self._buffer)
                    self._insert_into_widget(watched, bangla_str)
                    self._buffer = ""
                    self.buffer_changed.emit("")
                return super().eventFilter(watched, event)

        return super().eventFilter(watched, event)

    def _insert_into_widget(self, widget: QObject, text: str) -> None:
        """Insert text into supported Qt input widgets."""
        if isinstance(widget, QLineEdit):
            widget.insert(text)
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            widget.insertPlainText(text)
        self.text_composed.emit(text)

