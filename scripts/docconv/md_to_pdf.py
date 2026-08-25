"""Markdown -> PDF. Ayni HTML koprusunu md_to_epub ile paylasir.

Vendored: kaynak "C:\\Users\\Emre\\Desktop\\Pdf convertor\\converters\\md_to_pdf.py"
(kullanicinin kendi projesi). BILEREK FARKLILASTIRILDI: PDF'e kitap gorunumu icin ekstra
Calibre argumanlari eklendi (kagit boyutu, kenar bosluklari, hecele, iki yana yasla, sayfa
numarasi, TOC) -- orijinal projede yok. Kagit boyutu/kenar boslugu tercihleri disinda mantik
ayni, orijinal degisirse elle senkron tutulmali.
"""

import tempfile
from pathlib import Path

from . import calibre_wrapper, md_to_epub

# Calibre'nin PDF motoru CSS'i kismen yorumlar; kitap-gorunumu icin kritik olan
# hecele/iki-yana-yaslama/sayfa-numarasi/TOC ozelliklerini kendi bayraklariyla
# ayrica belirtiyoruz (ebook-convert --help ile dogrulandi).
_PDF_ARGS = [
    "--paper-size", "a5",
    "--pdf-page-margin-left", "54",
    "--pdf-page-margin-right", "54",
    "--pdf-page-margin-top", "60",
    "--pdf-page-margin-bottom", "60",
    # a5 fiziksel olarak kucuk bir sayfa; base-font-size vermezsek Calibre
    # varsayilan cikti profiline gore (buyukce bir sayfa varsayan) puanlar,
    # bu da a5'te orantisiz buyuk font olarak gorunur. 7 -> gercek renderda ~9.6pt,
    # normal bir cep kitabi govde metni yogunluguna denk geliyor (olculdu, dogrulandi).
    # NOT: bu deger tam sayi olmali, Calibre float kabul etmiyor.
    "--base-font-size", "7",
    "--change-justification", "justify",
    "--pdf-hyphenate",
    "--pdf-page-numbers",
    "--pdf-add-toc",
    "--level1-toc", "//h:h1",
    "--level2-toc", "//h:h2",
]


def convert(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_html = tmp_dir / "book.html"
        tmp_html.write_text(md_to_epub.markdown_to_html(input_path), encoding="utf-8")
        md_to_epub.copy_sibling_images(input_path, tmp_dir)
        calibre_wrapper.convert(tmp_html, output_path, extra_args=_PDF_ARGS)
