# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

added_files = [
    ('fonts', 'fonts'),
    ('icons', 'icons'),
]

hidden_imports = [
    'pymupdf',
    'uharfbuzz',
    'PIL',
    'PIL.Image',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'core',
    'core.annotations',
    'core.bangla_input',
    'core.page_tools',
    'core.pdf_engine',
    'core.text_renderer',
    'core.undo_redo',
    'ui',
    'ui.dialogs',
    'ui.i18n',
    'ui.main_window',
    'ui.pdf_view',
    'ui.properties_panel',
    'ui.themes',
    'ui.thumbnail_panel',
    'ui.toolbar',
    'ui.user_paths',
    'ui.welcome_screen',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
        'pyarrow',
        'IPython',
        'ipykernel',
        'pytest',
        'jupyter',
        'zmq',
        'tornado',
        'notebook',
        'sphinx',
        'setuptools',
        'pip',
        'wheel',
        'cryptography',
        'botocore',
        'boto3',
        'google',
        'django',
        'flask',
        'pygame',
        'numba',
        'sympy',
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
    [],
    exclude_binaries=True,
    name='RuhiPdfEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/app_icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RuhiPdfEditor',
)
