"""PDF -> Markdown.

Vendored: kaynak "C:\\Users\\Emre\\Desktop\\Pdf convertor\\converters\\pdf_to_md.py"
(kullanicinin kendi projesi). Elle senkron tutulmali -- orijinal degisirse buraya da tasi.

Fark: orijinal `from bootstrap import TESSERACT_COMMON_PATHS` kullanir; biz bootstrap.py'yi
(Calibre/Tesseract'i otomatik indirip kuran, UAC tetikleyen modul) BILEREK vendored etmedik --
bu proje sessizce/otomatik sistem kurulumu yapmamali. Sadece kullandigimiz sabiti burada
yerel olarak tanimliyoruz, geri kalan mantik birebir ayni.

Metin katmani olan sayfalar icin pymupdf4llm (yapi/tablo/baslik farkinda).
Metin katmani olmayan (taranmis) sayfalar icin sayfa goruntuye renderlanip
Tesseract OCR ile okunur - boylece karisik (bir kismi metin, bir kismi
taranmis) PDF'ler de calisir.
"""

import shutil
from pathlib import Path

import pymupdf as fitz
import pymupdf4llm
import pytesseract
from PIL import Image

TESSERACT_COMMON_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)

MIN_CHARS_PER_PAGE = 20
OCR_DPI = 300


def _resolve_tesseract() -> None:
    """PATH'te yoksa (yeni kurulmus olabilir, surec PATH'i henuz gormuyor
    olabilir) bilinen kurulum yerinden dogrudan tesseract.exe'yi bul."""
    if shutil.which("tesseract"):
        return
    for exe_path in TESSERACT_COMMON_PATHS:
        if exe_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(exe_path)
            return


def _resolve_ocr_langs() -> str:
    """Turkce paketi kurulmadiysa (indirme basarisiz olduysa) sadece
    Ingilizce'ye dus - aksi halde pytesseract 'tur' bulunamadi diye patlar."""
    tesseract_cmd = Path(pytesseract.pytesseract.tesseract_cmd)
    tessdata_dir = tesseract_cmd.parent / "tessdata"
    if (tessdata_dir / "tur.traineddata").exists():
        return "eng+tur"
    return "eng"


def _page_has_text(doc: "fitz.Document", page_index: int) -> bool:
    return len(doc[page_index].get_text().strip()) >= MIN_CHARS_PER_PAGE


def _ocr_page(doc: "fitz.Document", page_index: int, langs: str) -> str:
    page = doc[page_index]
    pix = page.get_pixmap(dpi=OCR_DPI)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(img, lang=langs)


def convert(input_path: Path, output_path: Path) -> None:
    doc = fitz.open(str(input_path))
    try:
        scanned_pages = {i for i in range(len(doc)) if not _page_has_text(doc, i)}

        if not scanned_pages:
            md_text = pymupdf4llm.to_markdown(str(input_path))
        else:
            _resolve_tesseract()
            langs = _resolve_ocr_langs()
            parts = []
            for i in range(len(doc)):
                parts.append(_ocr_page(doc, i, langs) if i in scanned_pages else doc[i].get_text())
            md_text = "\n\n".join(parts)
    finally:
        doc.close()

    output_path.write_text(md_text, encoding="utf-8")
