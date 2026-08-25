"""Bir kaynak dosyanin hangi ceviri yoluna uygun oldugunu belirler.

Cikti (JSON): {"format", "scanned", "diagram_heavy", "recommend"}
  recommend == "inplace"   -> translate-pdf-inplace (yerinde, diyagram/duzen korunur)
  recommend == "markdown"  -> translate-book markdown yolu (akan metin; epub/taranmis/az-diyagram)

Kullanim: python pdf_profile.py "<kaynak dosya yolu>"
"""
import json
import sys
from pathlib import Path

from docconv.pdf_to_md import MIN_CHARS_PER_PAGE


def profile(path: Path) -> dict:
    ext = path.suffix.lower()
    if ext == ".epub":
        return {"format": "epub", "scanned": False, "diagram_heavy": False, "recommend": "markdown"}
    if ext != ".pdf":
        return {"format": ext.lstrip("."), "scanned": False, "diagram_heavy": False, "recommend": "markdown"}

    import pymupdf as fitz
    doc = fitz.open(str(path))
    try:
        total = len(doc)
        if total == 0:
            return {"format": "pdf", "scanned": False, "diagram_heavy": False, "recommend": "markdown"}
        sparse = 0
        diagram_pages = 0
        for i in range(total):
            pg = doc[i]
            if len(pg.get_text().strip()) < MIN_CHARS_PER_PAGE:
                sparse += 1
            # vektor cizim (diyagram) ya da gomulu resim iceren sayfa
            if len(pg.get_drawings()) >= 6 or len(pg.get_images()) >= 1:
                diagram_pages += 1
    finally:
        doc.close()

    scanned = sparse > total * 0.5
    diagram_ratio = diagram_pages / total
    diagram_heavy = diagram_ratio >= 0.12  # sayfalarin >=%12'sinde diyagram/resim -> gorsel-agirlikli
    recommend = "inplace" if (not scanned and diagram_heavy) else "markdown"
    return {
        "format": "pdf", "scanned": scanned, "diagram_heavy": diagram_heavy,
        "diagram_ratio": round(diagram_ratio, 2), "total_pages": total,
        "recommend": recommend,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("HATA: kaynak dosya yolu gerekli.", file=sys.stderr)
        return 1
    print(json.dumps(profile(Path(sys.argv[1]).expanduser().resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
