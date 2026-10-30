# PDF Editor with Bangla Support

A fully offline desktop PDF editor built with Python, PySide6, and PyMuPDF — featuring proper **Bangla (Bengali) text shaping** with Avro-style phonetic input.

No internet connection required. No cloud services. Your documents stay on your machine.

---

## Features

1. **Open, View & Navigate PDFs** — Load any PDF, scroll through pages, zoom in/out, fit-to-width, and jump to specific pages.
2. **Add, Edit & Reposition Text** — Insert new text anywhere on a page with proper Bangla font shaping. Easily drag to reposition anywhere on the page, double-click to edit, and click the close handle or press Delete/Backspace to remove.
2b. **Erase / Delete Existing Text** — Use the dedicated Eraser tool (🧹) or right-click any existing text in the PDF to wipe it out cleanly using PDF redaction.
3. **Bangla Text Input (Avro Phonetic)** — Type Bangla using an Avro-style phonetic keyboard. Type in English letters and get Bangla output in real time (e.g., `bangladesh` → `বাংলাদেশ`).
4. **Highlight, Underline & Strikethrough** — Annotate PDFs with text markup tools. Choose custom colors for highlights.
5. **Freehand Drawing & Shapes** — Draw freehand lines, rectangles, circles, and arrows directly on PDF pages.
6. **Add & Manage Images** — Insert images (PNG, JPEG, BMP, SVG) onto PDF pages. Resize and reposition with drag handles.
7. **Page Management** — Add, delete, reorder, rotate, and duplicate pages. Merge multiple PDFs into one or split a PDF into parts.
8. **Undo / Redo** — Full undo/redo support with a command-based stack for all editing operations.
9. **Save & Export** — Save as PDF. Export pages as images (PNG, JPEG). Print directly from the application.
10. **Fully Offline** — Everything runs locally. No telemetry, no network calls, no accounts required.

---

## Screenshots

> *Screenshots coming soon. Run the application to see it in action.*

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.11 or higher |
| PySide6 | 6.5.0+ |
| PyMuPDF (fitz) | 1.23.0+ |
| OS | Windows 10/11, Linux, macOS |

---

## Installation and Setup

### 1. Clone or Download

```bash
git clone https://github.com/your-username/pdf-editor.git
cd pdf-editor
```

Or download and extract the ZIP archive.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **PySide6** — Qt 6 bindings for the GUI
- **PyMuPDF** — PDF rendering and manipulation engine

### 3. Set Up Fonts

The editor requires Bangla-capable fonts for proper text rendering. Run the font helper to check which fonts are installed:

```bash
python download_fonts.py
```

Download the following fonts and place the `.ttf` files in the `fonts/` directory:

#### Noto Sans Bengali (Required for Bangla)
- **URL:** https://fonts.google.com/noto/specimen/Noto+Sans+Bengali
- Download both **Regular** and **Bold** variants
- Files needed: `NotoSansBengali-Regular.ttf`, `NotoSansBengali-Bold.ttf`

#### Noto Sans (Required for English/Latin)
- **URL:** https://fonts.google.com/noto/specimen/Noto+Sans
- Download **Regular**, **Bold**, **Italic**, and **Bold Italic** variants
- Files needed: `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf`, `NotoSans-Italic.ttf`, `NotoSans-BoldItalic.ttf`

#### Kalpurush (Optional — alternative Bangla font)
- **URL:** https://github.com/AnsarulIslam/Kalpurush-Font
- Alternative: https://ekushey.org/kalpurush/
- File needed: `Kalpurush.ttf`

#### SolaimanLipi (Optional — alternative Bangla font)
- **URL:** https://github.com/AnsarulIslam/SolaimanLipi
- Alternative: https://ekushey.org/solaimanlipi/
- File needed: `SolaimanLipi.ttf`

After downloading, your `fonts/` directory should look like:

```
fonts/
├── NotoSansBengali-Regular.ttf
├── NotoSansBengali-Bold.ttf
├── NotoSans-Regular.ttf
├── NotoSans-Bold.ttf
├── NotoSans-Italic.ttf
├── NotoSans-BoldItalic.ttf
├── Kalpurush.ttf          (optional)
└── SolaimanLipi.ttf        (optional)
```

---

## Running the Application

### Launch the editor

```bash
python main.py
```

### Open a specific PDF file

```bash
python main.py path/to/your/file.pdf
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open PDF file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+N` | New document |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+P` | Print |
| `Ctrl+E` | Export page as image |
| `Ctrl++` / `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Fit to width |
| `Ctrl+1` | Actual size (100%) |
| `Page Up` | Previous page |
| `Page Down` | Next page |
| `Home` | First page |
| `End` | Last page |
| `Ctrl+G` | Go to page |
| `T` | Text tool |
| `H` | Highlight tool |
| `D` | Drawing tool |
| `I` | Image insert tool |
| `Escape` | Cancel current tool / Deselect |
| `Delete` / `Backspace` | Delete selected text box / annotation |
| `F11` | Toggle fullscreen |
| `Ctrl+Space` / `Ctrl+B` | Toggle Bangla input mode |

---

## Bangla Input

The editor includes an **Avro-style phonetic Bangla input engine**. When Bangla input mode is active (toggle with `Ctrl+B`), you type in English letters and the engine converts them to Bangla script in real time.

### How It Works

Type romanized Bangla and the engine transliterates it:

| You Type | Output |
|---|---|
| `ami` | আমি |
| `bangla` | বাংলা |
| `bangladesh` | বাংলাদেশ |
| `bishwobidyaloy` | বিশ্ববিদ্যালয় |
| `durga` | দুর্গা |
| `koushal` | কৌশল |

### Phonetic Mapping Examples

| Latin | Bangla | Name |
|---|---|---|
| `k` | ক | ko |
| `kh` | খ | kho |
| `g` | গ | go |
| `gh` | ঘ | gho |
| `ch` | চ | cho |
| `chh` | ছ | chho |
| `t` | ত | to |
| `th` | থ | tho |
| `d` | দ | do |
| `dh` | ধ | dho |
| `n` | ন | no |
| `p` | প | po |
| `ph` / `f` | ফ | pho |
| `b` | ব | bo |
| `bh` | ভ | bho |
| `m` | ম | mo |
| `sh` / `S` | শ | sho |
| `s` | স | so |
| `r` | র | ro |
| `l` | ল | lo |

### Vowels

| Latin | Bangla (Standalone) |
|---|---|
| `a` | অ |
| `aa` / `A` | আ |
| `i` | ই |
| `ii` / `I` | ঈ |
| `u` | উ |
| `uu` / `U` | ঊ |
| `e` | এ |
| `oi` | ঐ |
| `o` | ও |
| `ou` | ঔ |

The engine handles consonant conjuncts (যুক্তাক্ষর) automatically. For example, typing `kr` produces ক্র, and `st` produces স্ত.

---

## Building an Executable

You can package the application as a standalone executable using PyInstaller.

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build (Windows)

```bash
pyinstaller pdf_editor.spec
```

Or use the one-liner:

```bash
pyinstaller --name "PDF Editor" --windowed --onefile --add-data "fonts;fonts" --add-data "icons;icons" --hidden-import PySide6.QtSvg main.py
```

The output executable will be in the `dist/` directory.

### Build (Linux)

```bash
pyinstaller pdf_editor.spec
```

> **Note:** On Linux, the `--add-data` separator is `:` instead of `;`. If using the one-liner, replace `"fonts;fonts"` with `"fonts:fonts"`. The spec file handles this automatically.

### Build (macOS)

```bash
pyinstaller pdf_editor.spec
```

> **Note:** On macOS, you may need to add `--osx-bundle-identifier com.pdfeditor.app` for proper app bundle creation. Code signing may also be required for distribution.

---

## Project Structure

```
PDF Editor/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── pdf_editor.spec            # PyInstaller build configuration
├── download_fonts.py          # Font download helper script
├── README.md                  # This file
│
├── core/                      # Core business logic (no GUI)
│   ├── __init__.py
│   ├── pdf_engine.py          # PDF open/save/render via PyMuPDF
│   ├── text_renderer.py       # Text insertion with font shaping
│   ├── bangla_input.py        # Avro-style phonetic transliteration
│   ├── page_tools.py          # Page add/delete/rotate/merge/split
│   ├── annotation_tools.py    # Highlight, underline, strikethrough
│   ├── drawing_tools.py       # Freehand drawing and shapes
│   ├── image_tools.py         # Image insertion and manipulation
│   └── undo_redo.py           # Command-based undo/redo stack
│
├── ui/                        # PySide6 GUI components
│   ├── __init__.py
│   ├── main_window.py         # Main application window
│   ├── pdf_view.py            # PDF page viewer widget
│   ├── toolbar.py             # Toolbar with editing tools
│   ├── page_panel.py          # Page thumbnail sidebar
│   ├── property_panel.py      # Properties panel for selected objects
│   ├── text_edit_dialog.py    # Text editing dialog with Bangla support
│   ├── font_selector.py       # Font family/size/style selector
│   └── dialogs.py             # Export, print, merge, split dialogs
│
├── fonts/                     # Bundled font files (user-provided)
│   ├── NotoSansBengali-Regular.ttf
│   ├── NotoSansBengali-Bold.ttf
│   ├── NotoSans-Regular.ttf
│   └── ...
│
├── icons/                     # UI icons (SVG)
│   └── ...
│
└── tests/                     # Unit and integration tests
    ├── __init__.py
    ├── test_bangla_rendering.py
    ├── test_pdf_engine.py
    └── test_output/           # Generated test artifacts
```

---

## Running Tests

```bash
# Using pytest
python -m pytest tests/ -v

# Using unittest
python -m unittest discover tests/ -v

# Run a specific test file
python -m pytest tests/test_bangla_rendering.py -v
python -m pytest tests/test_pdf_engine.py -v
```

---

## Known Limitations

1. **No OCR for scanned PDFs** — The editor cannot edit text in scanned or image-based PDFs. An OCR engine (like Tesseract) would be needed for text recognition.

2. **Redact-and-replace text editing** — Editing existing text in a PDF uses a redact-and-replace approach: the original text area is covered with a white rectangle and new text is placed on top. The original text is removed from the PDF content.

3. **Complex PDF forms** — Interactive PDF forms with complex JavaScript, XFA forms, or advanced widget annotations may not be fully preserved after editing.

4. **Large PDF performance** — Very large PDFs (1000+ pages) may be slow to load and navigate. Page rendering is done on-demand to mitigate this, but the initial load may take time.

5. **Freehand drawing resolution** — Freehand drawing resolution depends on mouse sampling speed. Very fast mouse movements may result in jagged lines.

6. **Font substitution** — If the bundled fonts don't cover all required glyphs (e.g., rare Unicode characters), font substitution may occur and the rendered text may look different from the input preview.

7. **Text searchability** — Text inserted using `insert_htmlbox` may not be fully searchable or selectable in all PDF readers. This is a known limitation of the PDF format when using embedded fonts with complex scripts.

8. **No digital signatures** — The editor does not support creating or validating digital signatures on PDF documents.

9. **Single-page editing** — Annotations and drawings are applied one page at a time. There is no batch annotation mode across multiple pages.

10. **No PDF/A compliance** — Exported PDFs are standard PDFs and may not comply with PDF/A archival format requirements.

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2024 PDF Editor Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Credits

- **[PySide6](https://doc.qt.io/qtforpython-6/)** — Qt 6 for Python, providing the GUI framework. Licensed under LGPL.
- **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)** — PDF rendering and manipulation library. Licensed under AGPL v3 (or commercial).
- **[Noto Sans Bengali](https://fonts.google.com/noto/specimen/Noto+Sans+Bengali)** — Bengali font by Google. Licensed under SIL Open Font License 1.1.
- **[Noto Sans](https://fonts.google.com/noto/specimen/Noto+Sans)** — Latin/general font by Google. Licensed under SIL Open Font License 1.1.
- **[Kalpurush](https://ekushey.org/kalpurush/)** — Bangla font by Ekushey. Licensed under GPL with font exception.
- **[SolaimanLipi](https://ekushey.org/solaimanlipi/)** — Bangla font by Ekushey. Licensed under GPL with font exception.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

For Bangla-specific improvements (transliteration rules, font handling, text shaping), please include test cases in your PR.
