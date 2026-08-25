"""Yerinde (layout-preserving) PDF cevirisi icin bookkeeping + orkestrasyon.

Markdown yolunun (extract_book/next_batch/finish_batch) YERINDE-CEVIRI karsiligi. Kaynak
PDF'in duzenini/diyagramlarini/renklerini KORUR, sadece metni Turkce ile degistirir
(docconv/pdf_inplace.py motoru). Diyagram-agirlikli teknik kitaplar icin.

Disk = tek dogru kaynak (kesintiye dayanikli):
  books/<slug>/inplace/
    progress.json            - durum (SADECE bu scriptler yazar)
    pages/PPPP.json          - her sayfanin cevrilecek birimleri (kurulumda uretilir, sabit)
    pages_tr/PPPP.json       - cevrilmis birimler (text_tr dolu). VARLIGI ilerlemeyi belirler.
    batch_current.json       - siradaki batch'in birimleri (agent bunu cevirir)

Kullanim:
    python inplace_book.py setup   <slug> [--batch-pages N]
    python inplace_book.py next    <slug>          # siradaki batch (JSON) -> batch_current.json
    python inplace_book.py finish  <slug>          # batch_current_tr.json'u pages_tr/'ye dagit + render
    python inplace_book.py status  <slug>
    python inplace_book.py render  <slug>          # ceviriler/<Baslik>.pdf (kismi de olsa)
"""
import argparse
import io
import json
import sys
from pathlib import Path

import pymupdf as fitz

from bookutils import TRANSLATIONS_DIR, book_dir, load_progress, now_iso, safe_filename
from docconv import pdf_inplace

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

DEFAULT_BATCH_PAGES = 8


def _idir(slug: str) -> Path:
    return book_dir(slug) / "inplace"


def _source_pdf(slug: str) -> Path:
    return next(book_dir(slug).glob("source.pdf"))


def _prog_path(slug: str) -> Path:
    return _idir(slug) / "progress.json"


def load_iprog(slug: str) -> dict:
    return json.loads(_prog_path(slug).read_text(encoding="utf-8"))


def save_iprog(slug: str, data: dict) -> None:
    data["updated_at"] = now_iso()
    _prog_path(slug).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def setup(slug: str, batch_pages: int) -> dict:
    idir = _idir(slug)
    (idir / "pages").mkdir(parents=True, exist_ok=True)
    (idir / "pages_tr").mkdir(parents=True, exist_ok=True)
    if _prog_path(slug).exists():
        return load_iprog(slug)  # idempotent

    src = _source_pdf(slug)
    doc = fitz.open(str(src))
    total = len(doc)
    doc.close()

    # tum birimleri tek geciste cikar, sayfaya gore dagit
    all_units = pdf_inplace.extract_units(str(src), list(range(total)))
    by_page: dict[int, list] = {p: [] for p in range(total)}
    for u in all_units:
        by_page[u["page"]].append(u)
    for p in range(total):
        (idir / "pages" / f"{p:04d}.json").write_text(
            json.dumps(by_page[p], ensure_ascii=False), encoding="utf-8")

    title = load_progress(slug)["title"] if (book_dir(slug) / "progress.json").exists() else src.stem
    prog = {
        "slug": slug, "title": title, "source_pdf": str(src),
        "total_pages": total, "batch_pages": batch_pages,
        "translatable_units": len(all_units),
        "status": "in_progress", "created_at": now_iso(), "updated_at": now_iso(),
    }
    save_iprog(slug, prog)
    return prog


def _done_pages(slug: str) -> set[int]:
    """Cevrilmis sayfalar: pages_tr'de olanlar + hic cevrilecek birimi olmayan (bos/gorsel/
    tam-kod) sayfalar -- ikincisinde cevrilecek bir sey yok, olduklari gibi render edilir."""
    idir = _idir(slug)
    done = {int(p.stem) for p in (idir / "pages_tr").glob("*.json")}
    for p in (idir / "pages").glob("*.json"):
        if json.loads(p.read_text(encoding="utf-8")) == []:
            done.add(int(p.stem))
    return done


def status(slug: str) -> dict:
    prog = load_iprog(slug)
    done = _done_pages(slug)
    total = prog["total_pages"]
    prog["translated_pages"] = len(done)
    prog["status"] = "done" if len(done) >= total else "in_progress"
    save_iprog(slug, prog)
    return {"slug": slug, "title": prog["title"], "total_pages": total,
            "translated_pages": len(done), "status": prog["status"]}


def next_batch(slug: str) -> dict:
    prog = load_iprog(slug)
    total = prog["total_pages"]
    done = _done_pages(slug)
    pending = [p for p in range(total) if p not in done]
    if not pending:
        return {"status": "done", "slug": slug, "total_pages": total}

    batch = pending[: prog["batch_pages"]]
    units = []
    for p in batch:
        units.extend(json.loads((_idir(slug) / "pages" / f"{p:04d}.json").read_text(encoding="utf-8")))
    batch_file = _idir(slug) / "batch_current.json"
    batch_file.write_text(json.dumps(units, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "in_progress", "slug": slug, "pages": batch,
        "units_in_batch": len(units),
        "batch_file": str(batch_file),
        "batch_tr_file": str(_idir(slug) / "batch_current_tr.json"),
        "translated_pages_before": len(done), "total_pages": total,
    }


def finish_batch(slug: str) -> dict:
    """Agent'in yazdigi batch_current_tr.json'u sayfalara gore pages_tr/'ye dagitir."""
    tr_file = _idir(slug) / "batch_current_tr.json"
    units = json.loads(tr_file.read_text(encoding="utf-8"))
    by_page: dict[int, list] = {}
    for u in units:
        by_page.setdefault(u["page"], []).append(u)
    for p, us in by_page.items():
        (_idir(slug) / "pages_tr" / f"{p:04d}.json").write_text(
            json.dumps(us, ensure_ascii=False), encoding="utf-8")
    return status(slug)


def render(slug: str) -> dict:
    prog = load_iprog(slug)
    total = prog["total_pages"]
    done = _done_pages(slug)
    idir = _idir(slug)

    all_units = []
    for p in range(total):
        f_tr = idir / "pages_tr" / f"{p:04d}.json"
        f = f_tr if f_tr.exists() else idir / "pages" / f"{p:04d}.json"
        all_units.extend(json.loads(f.read_text(encoding="utf-8")))

    TRANSLATIONS_DIR.mkdir(exist_ok=True)
    out = TRANSLATIONS_DIR / f"{safe_filename(prog['title'])}.pdf"
    res = pdf_inplace.render(str(_source_pdf(slug)), all_units, str(out), list(range(total)))
    res["translated_pages"] = len(done)
    res["total_pages"] = total
    res["output"] = str(out)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["setup", "next", "finish", "status", "render"])
    ap.add_argument("slug")
    ap.add_argument("--batch-pages", type=int, default=DEFAULT_BATCH_PAGES)
    a = ap.parse_args()
    if a.mode == "setup":
        out = setup(a.slug, a.batch_pages)
    elif a.mode == "next":
        out = next_batch(a.slug)
    elif a.mode == "finish":
        out = finish_batch(a.slug)
    elif a.mode == "render":
        out = render(a.slug)
    else:
        out = status(a.slug)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
