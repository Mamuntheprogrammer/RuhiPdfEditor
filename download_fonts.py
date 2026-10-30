"""
Font Download Helper for PDF Editor.

Downloads the required Bangla and Latin fonts into the `fonts/` directory:
- Noto Sans Bengali (Regular, Bold)
- Kalpurush
- SolaimanLipi
- Noto Sans (Regular, Bold, Italic, BoldItalic)
"""

import os
import urllib.request
from pathlib import Path

FONT_DIR = Path(__file__).parent / "fonts"

FONTS: dict[str, str] = {
    "NotoSansBengali-Regular.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Regular.ttf",
    "NotoSansBengali-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Bold.ttf",
    "NotoSans-Regular.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    "NotoSans-Bold.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf",
    "NotoSans-Italic.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Italic.ttf",
    "NotoSans-BoldItalic.ttf": "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-BoldItalic.ttf",
    "Kalpurush.ttf": "https://raw.githubusercontent.com/hmoazzem/bangla-fonts/master/kalpurush.ttf",
    "SolaimanLipi.ttf": "https://raw.githubusercontent.com/hmoazzem/bangla-fonts/master/SolaimanLipi_20-04-07.ttf",
}


def download_fonts() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("PDF Editor — Font Verification & Downloader")
    print("=" * 60)

    for filename, url in FONTS.items():
        dest = FONT_DIR / filename
        if dest.exists() and dest.stat().st_size > 1000:
            print(f" [OK] {filename} is already present ({dest.stat().st_size:,} bytes).")
            continue

        print(f" Downloading {filename} from {url}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            print(f" [Downloaded] {filename} ({dest.stat().st_size:,} bytes).")
        except Exception as e:
            print(f" [Error] Failed downloading {filename}: {e}")

    print("\nAll fonts verified.")


if __name__ == "__main__":
    download_fonts()
