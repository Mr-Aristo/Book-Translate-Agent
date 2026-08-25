"""book.md -> book.pdf. "Pdf convertor" projesinden vendored edilen docconv/ paketiyle
(Calibre'nin ebook-convert'i uzerinden) hicbir arayuz olmadan, dogrudan fonksiyon
cagrisiyla calisir.

Kullanim:
    python book_to_pdf.py <slug>
    python book_to_pdf.py --input <herhangi bir .md dosyasi> --output <cikti.pdf>

Calibre kurulu degilse PDF yerine standalone HTML uretir (tarayicidan 'PDF olarak
yazdir' ile PDF alinabilir) -- ayni markdown_to_html() koprusu uzerinden, ekstra
bagimlilik gerektirmeden.
"""
import argparse
import json
import sys
from pathlib import Path

from bookutils import TRANSLATIONS_DIR, load_progress, safe_filename
from docconv import md_to_epub
from docconv.calibre_wrapper import CalibreNotFoundError
from docconv.md_to_pdf import convert as calibre_md_to_pdf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", nargs="?", help="ceviriler/<Kitap Basligi>.md kullanilir")
    parser.add_argument("--input", help="Dogrudan bir .md dosyasi (slug yerine)")
    parser.add_argument("--output", help="Cikti dosyasi (varsayilan: ceviriler/<Baslik>.pdf)")
    args = parser.parse_args()

    if not args.slug and not args.input:
        print("HATA: slug ya da --input gerekli.", file=sys.stderr)
        return 1

    if args.slug:
        title = load_progress(args.slug)["title"]
        # ceviriler/<Baslik>.md kullanilir (books/<slug>/book.md degil) -- dosya adinin
        # kendisi (stem) docconv.md_to_epub.markdown_to_html() tarafindan baslik olarak
        # kullaniliyor, "book.md" degil gercek kitap adi cikmali.
        md_path = TRANSLATIONS_DIR / f"{safe_filename(title)}.md"
        if not md_path.exists():
            print(f"HATA: {md_path} yok. Once en az bir batch cevrilmis olmali "
                  f"(book-translator agent'i / translate-book skill'i, finish_batch.py "
                  f"ceviriler/ altina yayinlar).", file=sys.stderr)
            return 1
        output = Path(args.output) if args.output else md_path.with_suffix(".pdf")
    else:
        md_path = Path(args.input).resolve()
        output = Path(args.output) if args.output else md_path.with_suffix(".pdf")

    try:
        calibre_md_to_pdf(md_path, output)
    except CalibreNotFoundError as exc:
        html_output = output.with_suffix(".html")
        html_output.write_text(md_to_epub.markdown_to_html(md_path), encoding="utf-8")
        print(json.dumps({
            "status": "fallback_html",
            "message": str(exc),
            "html_path": str(html_output),
        }, ensure_ascii=False, indent=2))
        print("Calibre bulunamadi. Bunun yerine HTML uretildi -- tarayicida acip "
              "'PDF olarak yazdir' ile PDF alabilirsin.", file=sys.stderr)
        return 0

    print(json.dumps({"status": "ok", "pdf_path": str(output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
