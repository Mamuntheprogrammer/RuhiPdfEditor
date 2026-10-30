# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PDF Editor.

Build command:
    pyinstaller pdf_editor.spec

Or one-liner:
    pyinstaller --name "PDF Editor" --windowed --onefile --add-data "fonts;fonts" --add-data "icons;icons" --hidden-import PySide6.QtSvg main.py
"""

import os
from pathlib import Path

block_cipher = None
project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'fonts'), 'fonts'),
        (os.path.join(project_root, 'icons'), 'icons'),
    ],
    hiddenimports=[
        'PySide6.QtSvg',
        'PySide6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
        'pytest', 'setuptools', 'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
)
