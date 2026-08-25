"""Ortak yardimci fonksiyonlar: slugify, progress.json okuma/yazma, batch hesaplama, assemble.

Tum scriptler (extract_book.py, next_batch.py, finish_batch.py, assemble_book.py, book_to_pdf.py)
bunu kullanir. Butun bookkeeping (ilerleme hesabi, tarih, JSON, birlestirme) burada yasar --
agent'in kendisi index/tarih/JSON hesabi yapmaz, sadece bu scriptleri cagirir.
"""
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# Windows konsolunda Python stdout varsayilani UTF-8 olmayabilir (orn. cp437) --
# bu da "ç"/"ş"/"ğ" gibi karakterleri JSON ciktisinda bozar. book-translator agent'i
# bu JSON'u okuyup dosya yollarini (orn. published_path) oldugu gibi kullanacagi icin
# bozuk metin gercek bir hataya donusur, sadece kozmetik degil.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
BOOKS_DIR = ROOT / "books"
TRANSLATIONS_DIR = ROOT / "çeviriler"

_TR_MAP = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def slugify(name: str) -> str:
    name = name.translate(_TR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name or "book"


def safe_filename(name: str) -> str:
    """Windows'ta dosya adi olarak gecersiz karakterleri temizler. Turkce karakterleri KORUR
    (sadece slug icin ASCII'ye indirgiyoruz, dosya adi icin gerek yok)."""
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "Kitap"


def book_dir(slug: str) -> Path:
    return BOOKS_DIR / slug


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_progress(slug: str) -> dict:
    path = book_dir(slug) / "progress.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(slug: str, data: dict) -> None:
    data["updated_at"] = now_iso()
    path = book_dir(slug) / "progress.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def progress_exists(slug: str) -> bool:
    return (book_dir(slug) / "progress.json").exists()


def sync_progress(slug: str) -> dict:
    """translated/ klasorundeki GERCEK dosyalara gore progress.json'u gunceller (self-healing).

    Ilerlemenin tek dogru kaynagi disktir, progress.json'daki sayac degil -- boylece bir batch
    yarida kesilse bile bir sonraki cagri gercek durumdan devam eder, sayac yalan soylemez.
    """
    progress = load_progress(slug)
    translated_dir = book_dir(slug) / "translated"
    total = progress["total_chunks"]

    done_indices = {int(p.stem) for p in translated_dir.glob("*.md")}
    completed = 0
    for i in range(1, total + 1):
        if i in done_indices:
            completed = i
        else:
            break  # ilk eksik chunk'ta dur - ceviri sirali ilerler

    progress["translated_chunks"] = completed
    progress["status"] = "done" if completed >= total else "in_progress"
    save_progress(slug, progress)
    return progress


def compute_next_batch(slug: str) -> dict:
    """Bir sonraki batch'te hangi raw/translated dosya ciftlerinin islenecegini dondurur.

    Agent bu fonksiyonun (next_batch.py CLI'i uzerinden) verdigi yollari OLDUGU GIBI kullanir,
    kendisi index/dolgu hesaplamaz.
    """
    if not progress_exists(slug):
        return {"status": "not_started", "slug": slug}

    progress = sync_progress(slug)
    total = progress["total_chunks"]
    completed = progress["translated_chunks"]

    if progress["status"] == "done":
        return {"status": "done", "slug": slug, "total_chunks": total, "translated_chunks": completed}

    bdir = book_dir(slug)
    batch_size = progress["chunks_per_run"]
    start = completed + 1
    end = min(total, completed + batch_size)
    batch = [
        {
            "index": i,
            "raw_path": str(bdir / "raw" / f"{i:04d}.md"),
            "translated_path": str(bdir / "translated" / f"{i:04d}.md"),
        }
        for i in range(start, end + 1)
    ]
    return {
        "status": "in_progress",
        "slug": slug,
        "total_chunks": total,
        "translated_chunks_before": completed,
        "batch": batch,
    }


def assemble(slug: str) -> dict:
    """translated/*.md'den book.md'yi yeniden uretir VE ceviriler/<Kitap Basligi>.md olarak yayinlar.

    ceviriler/ klasoru kullaniciya gosterilecek tek yer -- ic calisma klasoru (raw/translated/
    glossary/progress.json) orada gorunmez, sadece guncel (tam ya da kismi) ceviri.
    """
    progress = load_progress(slug)
    bdir = book_dir(slug)
    files = sorted((bdir / "translated").glob("*.md"), key=lambda p: int(p.stem))

    parts = [f"# {progress['title']}\n"]
    if progress["status"] != "done":
        parts.append(
            f"\n> Kismi ceviri: {progress['translated_chunks']}/{progress['total_chunks']} bolum tamamlandi.\n"
        )
    parts.append("\n---\n")
    for f in files:
        parts.append(f.read_text(encoding="utf-8"))
    content = "\n\n".join(parts)

    (bdir / "book.md").write_text(content, encoding="utf-8")

    TRANSLATIONS_DIR.mkdir(exist_ok=True)
    safe_title = safe_filename(progress["title"])
    published_path = TRANSLATIONS_DIR / f"{safe_title}.md"

    # ic kopyada (book.md) resim referanslari "images/x.png" olarak kalir (kendi images/
    # klasoruyle ayni dizinde). Yayinlanan kopya farkli bir klasorde (ceviriler/) oldugu
    # icin resimleri de oraya kopyalayip referanslari "<Baslik>_images/x.png" olarak
    # yeniden yaziyoruz -- aksi halde yayinlanan md'deki resimler kirik link olur.
    images_src = bdir / "images"
    published_content = content
    if images_src.is_dir() and any(images_src.iterdir()):
        images_dst = TRANSLATIONS_DIR / f"{safe_title}_images"
        images_dst.mkdir(exist_ok=True)
        for img_file in images_src.iterdir():
            if img_file.is_file():
                shutil.copy2(img_file, images_dst / img_file.name)
        published_content = re.sub(r"(!\[[^\]]*\]\()images/", rf"\1{safe_title}_images/", content)

    published_path.write_text(published_content, encoding="utf-8")

    return {
        "translated_files": len(files),
        "total_chunks": progress["total_chunks"],
        "status": progress["status"],
        "published_path": str(published_path),
    }
