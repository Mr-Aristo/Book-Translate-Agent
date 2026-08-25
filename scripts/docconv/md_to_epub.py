"""Markdown -> EPUB.

Vendored: kaynak "C:\\Users\\Emre\\Desktop\\Pdf convertor\\converters\\md_to_epub.py"
(kullanicinin kendi projesi). Elle senkron tutulmali -- orijinal degisirse buraya da tasi.

Markdown once basit bir HTML govdesine cevrilir, sonra Calibre bu HTML'i
EPUB3'e donusturur. level1/level2-toc argumanlari Calibre'ye H1/H2
basliklarindan gezinme (nav) tablosu uretmesini soyler - iPhone/Apple Books
gibi okuyucularda duzgun bir icindekiler menusu icin gerekli.
"""

import re
import shutil
import tempfile
from pathlib import Path

import markdown as md_lib

from . import calibre_wrapper


# Kitap-gorunumu tipografi. Govde serif (okunakli, klasik kitap hissi), basliklar
# sans-serif + KALIN (font-weight acikca 700 -- Calibre PDF motoru varsayilan UA
# stilini her zaman uygulamadigi icin bold'u burada zorunlu kiliyoruz; sikayet edilen
# "basliklar bold degil" sorunu buydu). Baslik hiyerarsisi boyut+bosluk+renk ile net.
_STYLE = """
html, body {
    column-count: 1 !important;
    -webkit-column-count: 1 !important;
    -moz-column-count: 1 !important;
}
body {
    font-family: "Palatino Linotype", Palatino, Georgia, "Noto Serif", "Times New Roman", serif;
    line-height: 1.5;
    margin: 1em;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    orphans: 2;
    widows: 2;
    color: #1a1a1a;
}
h1, h2, h3, h4 {
    font-family: "Segoe UI", "Helvetica Neue", Arial, "Noto Sans", sans-serif;
    font-weight: 700;
    line-height: 1.25;
    text-align: left;
    hyphens: none;
    -webkit-hyphens: none;
    color: #111111;
    page-break-after: avoid;
    break-after: avoid;
}
h1 {
    font-size: 2em;
    margin: 0 0 1.1em 0;
    padding-bottom: 0.25em;
    border-bottom: 2px solid #333333;
    page-break-before: always;
    break-before: page;
}
h1:first-of-type { page-break-before: avoid; break-before: avoid; }
h2 { font-size: 1.5em; margin: 1.8em 0 0.5em 0; }
h3 { font-size: 1.2em; margin: 1.4em 0 0.4em 0; color: #222222; }
h4 { font-size: 1.05em; margin: 1.2em 0 0.3em 0; color: #333333; }
p { margin: 0 0 0.35em 0; text-indent: 1.3em; }
h1 + p, h2 + p, h3 + p, h4 + p, blockquote p:first-child, li > p:first-child { text-indent: 0; }
a { color: #1a4a7a; text-decoration: none; }
blockquote {
    margin: 1.2em 1.6em;
    padding: 0.2em 0 0.2em 1em;
    border-left: 3px solid #bbbbbb;
    color: #444444;
    font-style: italic;
}
ul, ol { margin: 0.8em 0; padding-left: 1.6em; }
li { margin: 0.25em 0; text-align: left; }
img { max-width: 100%; height: auto; display: block; margin: 1.2em auto; }
table { width: 100%; border-collapse: collapse; margin: 1.2em 0; table-layout: auto; font-size: 0.95em; }
th, td {
    border: 1px solid #bbbbbb;
    padding: 0.45em 0.6em;
    text-align: left;
    vertical-align: top;
    word-wrap: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
}
th { background: #f0f0f0; font-weight: 700; }
pre {
    background: #f5f5f5;
    border: 1px solid #dddddd;
    border-radius: 4px;
    padding: 0.8em 1em;
    margin: 1em 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: Consolas, "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 0.85em;
    line-height: 1.4;
    page-break-inside: avoid;
}
code {
    font-family: Consolas, "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 0.88em;
    background: #f0f0f0;
    padding: 0.05em 0.3em;
    border-radius: 3px;
}
pre code { background: none; padding: 0; font-size: 1em; }
"""


# ---- Markdown normalizasyonu (yapiyi geri kazanma) --------------------------------
# Bazi kitaplar, eski/duz-metin cikarma yolundan gectikleri icin markdown yapisi
# tasimaz: basliklar `#` ile isaretli degildir, araya PDF sayfa numaralari ve tekrar
# eden ust-bilgiler karismistir. Bu, cikan PDF/EPUB'i "hepsi ayni puntoda duz metin"
# gibi gosterir. Asagidaki normalize_markdown, YENIDEN CEVIRI GEREKMEDEN convert
# aninda yapiyi geri kazanir: numarali/BUYUK-HARF basliklari `#`'e yukseltir, tek
# basina duran sayfa numarasi/ust-bilgi satirlarini atar. Zaten yapili (pymupdf4llm
# ile duzgun cikarilmis) kitaplarda etkisiz kalacak sekilde muhafazakar yazildi.

_PAGE_NUM_RE = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,7})\s*$", re.IGNORECASE)
_RUN_HDR_RE = re.compile(r"^\s*(BÖLÜM|BOLUM|CHAPTER)\s+\d+\s*$", re.IGNORECASE)
# Numarali bolum basligi: EN AZ bir nokta olmali (1.1, 1.2.3) -- "3 farkli yontem"
# gibi cumleleri yanlislikla baslik yapmamak icin tek-sayili "N Baslik" kabul edilmez.
_NUM_SEC_RE = re.compile(r"^(\d+(?:\.\d+){1,3})\s+(\S.*)$")


def _is_caps_heading(s: str) -> bool:
    """Satir tamamen BUYUK harf, kisa ve baslik gorunumundeyse True (Turkce-duyarli:
    str.upper() 'i'->'I', 'ş'->'Ş' donusumlerini dogru yapar). ISBN/baski-anahtari gibi
    sayi-agirlikli satirlari ve 'M A N N I N G' gibi harf-harf logo satirlarini eler."""
    if not (2 <= len(s) <= 70):
        return False
    letters = sum(c.isalpha() for c in s)
    if letters < 2:
        return False
    if sum(c.isdigit() for c in s) > letters:  # ISBN / baski anahtari / kod -> baslik degil
        return False
    if s != s.upper() or s == s.lower():
        return False
    if s.endswith((".", ":", ";", ",")):  # cumle/liste gibi bitenler baslik degildir
        return False
    tokens = s.split()
    if len(tokens) >= 3 and all(len(t) == 1 for t in tokens):  # "M A N N I N G" logo satiri
        return False
    return True


def _footer_noise(text: str) -> set[str]:
    """Cok sik (>10 kez) tekrar eden kisa duz satirlar = sayfa ust/alt-bilgisi veya filigran
    (orn. 'Bolum 1: ...', 'www.it-ebooks.info'). Bunlari genel olarak yakalayip atmak icin
    frekans sayar. KOD BLOKLARI (``` ici) haric tutulur -- tekrar eden kod satirlari ('}', '});')
    yanlislikla silinmesin."""
    from collections import Counter
    counts: Counter = Counter()
    in_code = False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s[0] in "#>|!-*+`":
            continue
        if len(s) <= 60:
            counts[s] += 1
    # Bolum ust-bilgisi deseni ("Bölüm 3: Paralel Temeller") -- 2+ kez tekrar ediyorsa ust-bilgidir
    # (gercek bolum basligi bir kez gecer). "Bölüm 3, ..." gibi virgullu ICERIK cumleleri KORUNUR.
    hdr = re.compile(r"^(Bölüm|Bolum|Chapter|BÖLÜM)\s+\d+\s*:", re.IGNORECASE)
    return {s for s, c in counts.items() if c > 10 or (c >= 2 and hdr.match(s))}


def normalize_markdown(text: str) -> str:
    out: list[str] = []
    seen_caps: set[str] = set()  # ayni BUYUK-HARF satiri tekrar ederse (ust-bilgi) yalnizca ilkini tut
    noise = _footer_noise(text)   # tekrar eden ust/alt-bilgi / filigran satirlari
    in_code = False
    close_idx: int | None = None  # son kapanan kod fence'inin out icindeki indeksi
    noise_in_gap = False          # o kapanmadan beri sayfa-siniri gurultusu atildi mi?

    def _break_gap():  # gercek icerik geldi -> kod birlestirme imkani biter
        nonlocal close_idx, noise_in_gap
        close_idx, noise_in_gap = None, False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        # Kod blogu fence'i (``` ... ```).
        if stripped.startswith("```"):
            if in_code:  # KAPANIS
                in_code = False
                out.append(line)
                close_idx, noise_in_gap = len(out) - 1, False
            else:  # ACILIS -- onceki blok sayfa-siniri gurultusuyle bolunmusse birlestir
                if close_idx is not None and noise_in_gap and all(o.strip() == "" for o in out[close_idx + 1:]):
                    del out[close_idx:]          # kapanis fence'i + aradaki bos satirlari kaldir
                    in_code = True               # onceki blogu yeniden ac (acilis fence'i yazma)
                    close_idx, noise_in_gap = None, False
                else:
                    in_code = True
                    out.append(line)
                    close_idx = None
            continue
        if in_code:
            out.append(line)
            continue
        if not stripped:
            out.append("")  # bos satir: gap'i bozmaz (kod arasi sayfa boslugu olabilir)
            continue
        # Tekrar eden alt/ust-bilgi / filigran -> at (sayfa-siniri isareti).
        if stripped in noise:
            noise_in_gap = True
            continue
        # Bos baslik (`#`, `## ` gibi metinsiz) -> at.
        if re.match(r"^#+\s*$", stripped):
            continue
        # Tek basina duran ayrac/boru (`|`) -> at (PDF sutun-ayrac artigi / sayfa-siniri).
        if re.fullmatch(r"[|│]+", stripped):
            noise_in_gap = True
            continue
        # PDF gurultusu: tek basina duran sayfa numarasi / tekrar eden ust-bilgi -> at.
        if _PAGE_NUM_RE.match(stripped) or _RUN_HDR_RE.match(stripped):
            noise_in_gap = True
            continue
        # Zaten yapili (baslik/alinti/tablo/resim/liste) satirlara dokunma.
        if stripped[0] in "#>|!-*+`" or re.match(r"^\d+[.)]\s", stripped):
            out.append(line)
            _break_gap()
            continue
        # Numarali bolum basligi (1.1 -> H2, 1.1.1 -> H3) -- kisa olmali (baslik, cumle degil).
        m = _NUM_SEC_RE.match(stripped)
        if m and len(m.group(2).split()) <= 12:
            level = min(m.group(1).count(".") + 1, 4)
            out.append(f"{'#' * level} {stripped}")
            _break_gap()
            continue
        # Tamamen BUYUK harf kisa satir -> alt baslik (H3). Tekrar edenler ilk gecisten sonra atilir.
        if _is_caps_heading(stripped):
            _break_gap()
            if stripped in seen_caps:
                continue
            seen_caps.add(stripped)
            out.append(f"### {stripped}")
            continue
        out.append(line)
        _break_gap()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def copy_sibling_images(input_path: Path, dest_dir: Path) -> None:
    """input_path'in yaninda <stem>_images/ klasoru varsa (bookutils.assemble()'in
    ceviriler/ altina yayinladigi resimler), Calibre'nin okuyacagi gecici HTML'in
    yanina da kopyalar -- aksi halde HTML'deki goreli ![](..._images/x.png)
    referanslari Calibre tarafindan cozulmez ve resimler cikan PDF/EPUB'ta kaybolur."""
    images_dir = input_path.parent / f"{input_path.stem}_images"
    if images_dir.is_dir():
        shutil.copytree(images_dir, dest_dir / images_dir.name, dirs_exist_ok=True)


def markdown_to_html(input_path: Path) -> str:
    text = normalize_markdown(input_path.read_text(encoding="utf-8"))
    body = md_lib.markdown(text, extensions=["tables", "fenced_code", "toc"])
    title = input_path.stem
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{_STYLE}</style></head><body>{body}</body></html>"
    )


def convert(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_html = tmp_dir / "book.html"
        tmp_html.write_text(markdown_to_html(input_path), encoding="utf-8")
        copy_sibling_images(input_path, tmp_dir)
        calibre_wrapper.convert(
            tmp_html,
            output_path,
            extra_args=[
                "--authors", "Unknown",
                "--level1-toc", "//h:h1",
                "--level2-toc", "//h:h2",
            ],
        )
