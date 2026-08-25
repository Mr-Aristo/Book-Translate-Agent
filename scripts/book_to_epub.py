"""book.md -> book.epub. "Pdf convertor" projesinden vendored edilen docconv/ paketiyle
(Calibre'nin ebook-convert'i uzerinden) hicbir arayuz olmadan, dogrudan fonksiyon
cagrisiyla calisir.

Kullanim:
    python book_to_epub.py <slug>
    python book_to_epub.py --input <herhangi bir .md dosyasi> --output <cikti.epub>

PDF'in aksine epub icin anlamli bir HTML-fallback yok (cikti tanim geregi .epub olmali) --
Calibre kurulu degilse hata verir.
"""
import argparse
import json
import sys
from pathlib import Path

from bookutils import TRANSLATIONS_DIR, load_progress, safe_filename
from docconv.calibre_wrapper import CalibreNotFoundError
from docconv.md_to_epub import convert as calibre_md_to_epub


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", nargs="?", help="ceviriler/<Kitap Basligi>.md kullanilir")
    parser.add_argument("--input", help="Dogrudan bir .md dosyasi (slug yerine)")
    parser.add_argument("--output", help="Cikti dosyasi (varsayilan: ceviriler/<Baslik>.epub)")
    args = parser.parse_args()

    if not args.slug and not args.input:
        print("HATA: slug ya da --input gerekli.", file=sys.stderr)
        return 1

    if args.slug:
        title = load_progress(args.slug)["title"]
        md_path = TRANSLATIONS_DIR / f"{safe_filename(title)}.md"
        if not md_path.exists():
            print(f"HATA: {md_path} yok. Once en az bir batch cevrilmis olmali "
                  f"(book-translator agent'i / translate-book skill'i, finish_batch.py "
                  f"ceviriler/ altina yayinlar).", file=sys.stderr)
            return 1
        output = Path(args.output) if args.output else md_path.with_suffix(".epub")
    else:
        md_path = Path(args.input).resolve()
        output = Path(args.output) if args.output else md_path.with_suffix(".epub")

    try:
        calibre_md_to_epub(md_path, output)
    except CalibreNotFoundError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"status": "ok", "epub_path": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
