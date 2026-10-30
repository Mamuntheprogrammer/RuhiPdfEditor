"""
Generates clean, highly professional 24x24 SVG vector icons for the PDF Editor toolbar.
Designed in the modern Lucide / Feather icon system with crisp 2px strokes, rounded caps and joins.
Uses pure vector paths with high-contrast colors suitable for both light and dark themes.
"""

from pathlib import Path

ICON_DIR = Path(__file__).parent / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

# Colors:
# - Primary slate: #334155 (slate-700)
# - Accent blue: #0284c7 (sky-600)
# - Danger red: #ef4444 (red-500)
# - Warning amber: #f59e0b (amber-500)
# - Success green: #10b981 (emerald-500)

ICONS: dict[str, str] = {
    # 1. Open (File folder)
    "open.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
  <path d="M2 10h20"/>
</svg>""",

    # 2. Save (Floppy disk)
    "save.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
  <polyline points="17 21 17 13 7 13 7 21"/>
  <polyline points="7 3 7 8 15 8"/>
</svg>""",

    # 3. Undo (Curved return arrow)
    "undo.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9 14 4 9l5-5"/>
  <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11"/>
</svg>""",

    # 4. Redo (Curved forward arrow)
    "redo.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m15 14 5-5-5-5"/>
  <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13"/>
</svg>""",

    # 5. Delete (Trash Can in warning red)
    "delete.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 6h18"/>
  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
  <line x1="10" x2="10" y1="11" y2="17"/>
  <line x1="14" x2="14" y1="11" y2="17"/>
</svg>""",

    # 6. Select (Clean mouse pointer)
    "select.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m3 3 7 18 3.5-7.5L21 10z"/>
</svg>""",

    # 7. Text Tool (Clean Typography "T" with frame)
    "text.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="4 7 4 4 20 4 20 7"/>
  <line x1="12" x2="12" y1="4" y2="20"/>
  <line x1="8" x2="16" y1="20" y2="20"/>
</svg>""",

    # 8. Highlight Tool (Chisel highlighter pen with neon accent)
    "highlight.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m9 11-6 6v3h3l6-6"/>
  <path d="m22 7-4.5-4.5a2.12 2.12 0 0 0-3 0L7 10l5 5 7.5-7.5a2.12 2.12 0 0 0 0-3Z"/>
  <line x1="14" x2="17" y1="5" y2="8"/>
</svg>""",

    # 9. Underline (Typography "U" with bar)
    "underline.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 4v6a6 6 0 0 0 12 0V4"/>
  <line x1="4" x2="20" y1="20" y2="20"/>
</svg>""",

    # 10. Strikethrough ("S" with central strike bar)
    "strikethrough.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M16 4H9a3 3 0 0 0-2.83 4"/>
  <path d="M14 12a4 4 0 0 1 0 8H6"/>
  <line x1="4" x2="20" y1="12" y2="12"/>
</svg>""",

    # 11. Rectangle (Geometric box)
    "rectangle.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect width="18" height="14" x="3" y="5" rx="2"/>
</svg>""",

    # 12. Line (Straight vector stroke)
    "line.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="4" x2="20" y1="20" y2="4"/>
  <circle cx="4" cy="20" r="1.5" fill="#334155"/>
  <circle cx="20" cy="4" r="1.5" fill="#334155"/>
</svg>""",

    # 13. Arrow (Directional vector)
    "arrow.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="5" x2="19" y1="19" y2="5"/>
  <polyline points="9 5 19 5 19 15"/>
</svg>""",

    # 14. Pen / Freehand (Drafting pen)
    "pen.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
  <path d="m15 5 4 4"/>
</svg>""",

    # 15. Image (Picture landscape)
    "image.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
  <circle cx="9" cy="9" r="2"/>
  <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
</svg>""",

    # 16. Signature (Quill / Ink stroke)
    "signature.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 21H3"/>
  <path d="M7 16c1.5-2 3-5 5-5s2.5 2 4 2 2-1 2-2"/>
  <path d="M5 12c1-2 2-6 4-6s2 2 3 5"/>
</svg>""",

    # 17. Eraser (Angled block with band)
    "eraser.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/>
  <path d="M22 21H7"/>
  <path d="m5 11 9 9"/>
</svg>""",

    # 18. Zoom In (Magnifier with plus)
    "zoom-in.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/>
  <line x1="21" x2="16.65" y1="21" y2="16.65"/>
  <line x1="11" x2="11" y1="8" y2="14"/>
  <line x1="8" x2="14" y1="11" y2="11"/>
</svg>""",

    # 19. Zoom Out (Magnifier with minus)
    "zoom-out.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="11" cy="11" r="8"/>
  <line x1="21" x2="16.65" y1="21" y2="16.65"/>
  <line x1="8" x2="14" y1="11" y2="11"/>
</svg>""",

    # 20. Bangla (Pure vector ligature badge with green border and stylized 'অ' shape)
    "bangla.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none">
  <rect x="2" y="3" width="20" height="18" rx="4" fill="#059669"/>
  <!-- Pure vector paths for Bengali letter 'অ' -->
  <path d="M12 6.5h7" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M17.5 6.5v11" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>
  <circle cx="8" cy="9" r="1.5" fill="#ffffff"/>
  <path d="M8 10.5c0 2 2.5 3 4.5 3" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M12.5 13.5h5" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/>
</svg>""",

    # 21. Bold (Text formatting)
    "bold.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 12h9a4 4 0 0 1 0 8H6z"/>
  <path d="M6 4h8a4 4 0 0 1 0 8H6z"/>
</svg>""",

    # 22. Bold White (for active/checked state)
    "bold-white.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 12h9a4 4 0 0 1 0 8H6z"/>
  <path d="M6 4h8a4 4 0 0 1 0 8H6z"/>
</svg>""",

    # 23. Italic (Text formatting)
    "italic.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <line x1="19" x2="10" y1="4" y2="4"/>
  <line x1="14" x2="5" y1="20" y2="20"/>
  <line x1="15" x2="9" y1="4" y2="20"/>
</svg>""",

    # 24. Italic White (for active/checked state)
    "italic-white.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <line x1="19" x2="10" y1="4" y2="4"/>
  <line x1="14" x2="5" y1="20" y2="20"/>
  <line x1="15" x2="9" y1="4" y2="20"/>
</svg>""",

    # 25. Palette (Color palette)
    "palette.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="13.5" cy="6.5" r=".5" fill="#334155"/>
  <circle cx="17.5" cy="10.5" r=".5" fill="#334155"/>
  <circle cx="8.5" cy="7.5" r=".5" fill="#334155"/>
  <circle cx="6.5" cy="12.5" r=".5" fill="#334155"/>
  <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.563-2.512 5.563-5.563C22 6.5 17.5 2 12 2Z"/>
</svg>""",
}


def generate_all() -> None:
    for name, content in ICONS.items():
        path = ICON_DIR / name
        path.write_text(content.strip(), encoding="utf-8")
    print(f"Generated {len(ICONS)} icons in {ICON_DIR}")


if __name__ == "__main__":
    generate_all()
