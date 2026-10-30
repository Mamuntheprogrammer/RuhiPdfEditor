"""
Standard user directory locations for professional desktop file dialogs.
Remembers the last visited PDF and image directories across sessions using QSettings.
"""

from __future__ import annotations

import os
from PySide6.QtCore import QSettings, QStandardPaths


class UserPathsManager:
    """Manages standard user directories for file open and save dialogs."""

    SETTINGS_KEY_PDF = "Paths/LastPdfDir"
    SETTINGS_KEY_IMAGE = "Paths/LastImageDir"

    @classmethod
    def get_last_pdf_dir(cls) -> str:
        """Return the last visited PDF directory, defaulting to the user's Documents folder."""
        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        saved = settings.value(cls.SETTINGS_KEY_PDF, "")
        if saved and os.path.isdir(str(saved)):
            return str(saved)
        # Default to standard User Documents folder
        doc_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        if doc_dir and os.path.isdir(doc_dir):
            return doc_dir
        # Fallback to User Home folder
        home_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation)
        if home_dir and os.path.isdir(home_dir):
            return home_dir
        return os.path.expanduser("~")

    @classmethod
    def set_last_pdf_dir(cls, file_or_dir_path: str) -> None:
        """Store the directory of a recently opened or saved PDF."""
        if not file_or_dir_path:
            return
        folder = file_or_dir_path if os.path.isdir(file_or_dir_path) else os.path.dirname(file_or_dir_path)
        if folder and os.path.isdir(folder):
            settings = QSettings("RuhiPdf", "RuhiPdfEditor")
            settings.setValue(cls.SETTINGS_KEY_PDF, folder)

    @classmethod
    def get_last_image_dir(cls) -> str:
        """Return the last visited image directory, defaulting to the user's Pictures folder."""
        settings = QSettings("RuhiPdf", "RuhiPdfEditor")
        saved = settings.value(cls.SETTINGS_KEY_IMAGE, "")
        if saved and os.path.isdir(str(saved)):
            return str(saved)
        # Default to standard User Pictures folder
        pic_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        if pic_dir and os.path.isdir(pic_dir):
            return pic_dir
        return cls.get_last_pdf_dir()

    @classmethod
    def set_last_image_dir(cls, file_or_dir_path: str) -> None:
        """Store the directory of a recently opened image or signature."""
        if not file_or_dir_path:
            return
        folder = file_or_dir_path if os.path.isdir(file_or_dir_path) else os.path.dirname(file_or_dir_path)
        if folder and os.path.isdir(folder):
            settings = QSettings("RuhiPdf", "RuhiPdfEditor")
            settings.setValue(cls.SETTINGS_KEY_IMAGE, folder)

