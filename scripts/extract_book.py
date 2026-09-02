"""Kaynak PDF/EPUB'u okuyup ceviri icin parcalara (chunk) bolen kurulum scripti.

Kullanim:
    python extract_book.py "<kaynak dosya yolu>" [--slug SLUG] [--chunk-words N] [--batch-size N]

Idempotent: progress.json zaten varsa hicbir sey yapmadan cikar (0 exit code).
Cikti: books/<slug>/{source.<ext>, raw/0001.md.., glossary.md, progress.json}
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from bookutils import BOOKS_DIR, book_dir, now_iso, progress_exists, save_progress, slugify
from docconv.pdf_to_md import MIN_CHARS_PER_PAGE
from docconv.pdf_to_md import convert as docconv_pdf_to_md

DEFAULT_CHUNK_WORDS = 2000
DEFAULT_BATCH_SIZE = 6

# Kitabin YARISINDAN fazlasi metinsizse gercekten taranmis (goruntu-tabanli) bir PDF'tir
# ve OCR yoluna gitmesi gerekir. Bunun ALTINDA kalan birkac seyrek sayfa (kapak, bolum
# ayraci, part basligi, tam-sayfa diyagram, bos sayfa) NORMALDIR ve kitabi taranmis
# saydirmamalidir -- aksi halde metin-katmanli bir kitap sirf birkac seyrek sayfasi var
# diye resim-cikarmayan OCR yoluna dusup butun diyagramlarini kaybeder.
SCANNED_PAGE_RATIO = 0.5


def _pdf_is_scanned(path: Path) -> bool:
    import pymupdf as fitz
    doc = fitz.open(str(path))
    try:
        total = len(doc)
        if total == 0:
            return False
        sparse = sum(1 for i in range(total) if len(doc[i].get_text().strip()) < MIN_CHARS_PER_PAGE)
        return sparse > total * SCANNED_PAGE_RATIO
    finally:
        doc.close()


def extract_pdf(path: Path, images_dir: Path) -> str:
    """Metin katmanli PDF'lerde resimleri de cikarir (images_dir'e, goreli 'images/x.png'
    referanslariyla). Sadece kitabin BUYUK cogunlugu metinsizse (gercekten taranmis PDF)
    docconv/pdf_to_md.py'nin OCR yoluna devreder -- o yolda resim cikarma desteklenmiyor
    (bilinen sinir, taranmis sayfada diyagram kaybolur). Birkac seyrek sayfasi olan normal
    metin-katmanli kitaplar bu yola DUSMEZ, resimleriyle birlikte pymupdf4llm ile cikar."""
    if _pdf_is_scanned(path):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_md = Path(tmp) / "extracted.md"
            docconv_pdf_to_md(path, tmp_md)
            return tmp_md.read_text(encoding="utf-8")

    import pymupdf4llm

    images_dir.mkdir(parents=True, exist_ok=True)
    # pymupdf4llm, image_path'i markdown referansina OLDUGU GIBI (goreli/mutlak farketmeksizin)
    # gomer. Tasinabilirlik icin goreli "images" veriyoruz, bu yuzden gercek dosyalarin da
    # kitap klasorune goreli yazilmasi icin gecici olarak oraya chdir ediyoruz.
    old_cwd = os.getcwd()
    os.chdir(images_dir.parent)
    try:
        return pymupdf4llm.to_markdown(str(path), write_images=True, image_path="images", image_format="png")
    finally:
        os.chdir(old_cwd)


def extract_epub(path: Path, images_dir: Path) -> str:
    import html2text
    from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE

    book = epub.read_epub(str(path))

    image_map: dict[str, str] = {}
    epub_images = list(book.get_items_of_type(ITEM_IMAGE))
    if epub_images:
        images_dir.mkdir(parents=True, exist_ok=True)
        for item in epub_images:
            safe_name = item.get_name().replace("/", "_").replace("\\", "_")
            (images_dir / safe_name).write_bytes(item.get_content())
            image_map[item.get_name()] = safe_name
            image_map[Path(item.get_name()).name] = safe_name

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = not image_map

    parts = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        html = item.get_content().decode("utf-8", errors="ignore")
        md = converter.handle(html).strip()
        if md:
            parts.append(md)
    combined = "\n\n".join(parts)

    if not image_map:
        return combined

    def _rewrite(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        local = image_map.get(src) or image_map.get(Path(src).name)
        return f"![{alt}](images/{local})" if local else m.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _rewrite, combined)


def split_into_chunks(text: str, chunk_words: int) -> list[str]:
    # Bos satirlara gore paragraflara bol, baslik satirlarini yumusak sinir olarak kullan.
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    heading_re = re.compile(r"^#{1,3}\s")

    for para in paragraphs:
        para = para.strip("\n")
        if not para.strip():
            continue
        para_words = len(para.split())
        is_heading = bool(heading_re.match(para.strip()))

        if is_heading and current_words >= chunk_words * 0.4:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

        current.append(para)
        current_words += para_words

        if current_words >= chunk_words:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Kaynak PDF veya EPUB dosyasinin yolu")
    parser.add_argument("--slug", help="Kitap klasoru icin kisa ad (verilmezse dosya adindan uretilir)")
    parser.add_argument("--title", help="Yayinlanan ceviri dosyasinin basligi (verilmezse kaynak dosya adindan). "
                        "Can Yucel/yerinde gibi farkli ceviri yollari ayni kitabi ayri baslikla yayinlayabilsin diye.")
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                         help="book-translator agent'inin tek calismada cevirecegi chunk sayisi")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"HATA: kaynak dosya bulunamadi: {source}", file=sys.stderr)
        return 1

    ext = source.suffix.lower()
    if ext not in (".pdf", ".epub"):
        print(f"HATA: desteklenmeyen format: {ext} (sadece .pdf ve .epub)", file=sys.stderr)
        return 1

    slug = args.slug or slugify(source.stem)
    bdir = book_dir(slug)

    if progress_exists(slug):
        from bookutils import load_progress
        existing = load_progress(slug)
        existing_source = Path(existing["source_path"]).resolve()
        if existing_source != source:
            print(f"HATA: '{slug}' zaten FARKLI bir kaynakla kurulu ({existing_source}).\n"
                  f"Bu ayni isimli baska bir kitap olabilir -- --slug ile farkli bir ad ver.",
                  file=sys.stderr)
            return 1
        print(f"'{slug}' zaten kurulu, extract atlaniyor (books/{slug}/progress.json mevcut).")
        return 0

    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "raw").mkdir(exist_ok=True)
    (bdir / "translated").mkdir(exist_ok=True)

    dest_source = bdir / f"source{ext}"
    shutil.copy2(source, dest_source)

    images_dir = bdir / "images"

    print(f"Metin cikariliyor ({ext})...")
    raw_text = extract_pdf(dest_source, images_dir) if ext == ".pdf" else extract_epub(dest_source, images_dir)

    if not raw_text.strip():
        print("HATA: cikarilan metin bos. Dosya taranmis/gorsel-tabanli bir PDF olabilir (OCR gerekir).",
              file=sys.stderr)
        return 1

    chunks = split_into_chunks(raw_text, args.chunk_words)
    for i, chunk in enumerate(chunks, start=1):
        (bdir / "raw" / f"{i:04d}.md").write_text(chunk, encoding="utf-8")

    glossary_path = bdir / "glossary.md"
    if not glossary_path.exists():
        glossary_path.write_text(
            "# Terim Sozlugu\n\n"
            "Ozel isimler ve tekrar eden terimlerin tutarli cevirisi icin.\n"
            "book-translator agent'i her batch'te bu dosyayi okur ve yeni terim eklerse gunceller.\n\n"
            "| Orijinal | Turkce Ceviri | Not |\n|---|---|---|\n",
            encoding="utf-8",
        )

    total_words = len(raw_text.split())
    save_progress(slug, {
        "title": args.title or source.stem,
        "slug": slug,
        "source_path": str(source),
        "source_format": ext.lstrip("."),
        "target_language": "tr",
        "status": "in_progress",
        "total_chunks": len(chunks),
        "translated_chunks": 0,
        "chunks_per_run": args.batch_size,
        "total_words_estimate": total_words,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })

    print(f"Kurulum tamam: '{slug}' -> {len(chunks)} chunk, ~{total_words} kelime.")
    print(f"Klasor: {bdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
