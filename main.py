"""
PDF Editor with Bangla Support
==============================
A fully offline desktop PDF editor with proper Bangla (Bengali) text shaping.

Usage:
    python main.py [pdf_file]
"""
import os
import sys
from pathlib import Path

# Suppress PyMuPDF fitz deprecation warning by aliasing pymupdf directly
try:
    import pymupdf as fitz
    sys.modules.setdefault("fitz", fitz)
except ImportError:
    pass

def setup_environment() -> None:
    """Set up the application environment.
    - Add project root to sys.path
    - Set environment variables for Qt
    - Register bundled fonts
    """
    # Ensure project root is on path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # For PyInstaller frozen builds
    if getattr(sys, 'frozen', False):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(
            Path(sys._MEIPASS) / 'PySide6' / 'plugins' / 'platforms'
        )

def main() -> int:
    """Main entry point."""
    setup_environment()
    
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from ui.main_window import MainWindow
    
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("RuhiPdf Editor")
    app.setApplicationDisplayName("RuhiPdf Editor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Md. Abdullah Al Mamun")
    app.setOrganizationDomain("github.com/Mamuntheprogrammer")

    app_icon_path = Path(__file__).parent / "icons" / "app_icon.png"
    if app_icon_path.exists():
        app.setWindowIcon(QIcon(str(app_icon_path)))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Open file from command line argument if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
            window.open_file(file_path)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
