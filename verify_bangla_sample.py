import fitz
import sys
sys.stdout.reconfigure(encoding='utf-8')
from core.text_renderer import TextRenderer
from core.bangla_input import BanglaPhoneticEngine

engine = BanglaPhoneticEngine()
test_words = ['bangladesh', 'bishwobidyaloy', 'kshotriyo', 'durga', 'koushal', 'ami banglay gan gai']

print("Transliteration test:")
for w in test_words:
    bng = engine.transliterate(w)
    print(f"  {w:22} -> {bng}")

renderer = TextRenderer()
doc = fitz.open()
page = doc.new_page(width=595, height=842)

y = 50
for w in test_words:
    bng = engine.transliterate(w)
    renderer.insert_text_to_page(
        page,
        (50, y, 500, y + 40),
        bng,
        font_family="Noto Sans Bengali",
        font_size=16,
    )
    y += 50

out_path = "tests/bangla_sample_verified.pdf"
doc.save(out_path)
doc.close()

verify_doc = fitz.open(out_path)
print(f"\nSaved PDF: {out_path}")
print(f"Page count: {verify_doc.page_count}")
for i, p in enumerate(verify_doc):
    fonts = p.get_fonts()
    print(f"Page {i+1} embedded fonts:")
    for f in fonts:
        print(f"  - {f}")
    text = p.get_text()
    print(f"Page {i+1} extracted text snippet:\n{text[:200]}")
verify_doc.close()
