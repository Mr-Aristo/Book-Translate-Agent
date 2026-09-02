"""Yerinde (layout-preserving) PDF cevirisi.

Orijinal PDF'in vektor diyagramlarini, resimlerini, renklerini ve sayfa duzenini
KORUR; yalnizca metni kaldirip yerine Turkce'yi ayni konuma basar. Diyagram-agirlikli
teknik kitaplar icin markdown yolundan cok daha sadik sonuc verir.

Boru hatti (skill tarafindan surulur):
  1. extract_units(pdf, pages) -> her cevrilecek metin biriminin konum/font/renk bilgisi (JSON)
  2. (LLM) her birimin `text_tr` alanini doldurur -- kod/monospace bloklar cevrilmez
  3. render(pdf, units_tr, out_pdf) -> metni redaksiyonla kaldirir (grafik KORUNUR),
     Turkce'yi Turkce-uyumlu serif fontla ayni yere basar (sigmazsa fontu kucultur)

Font: Windows'ta Times New Roman / Georgia gibi tam Turkce glif iceren serifler. Kitap
gorunumu icin serif tercih edilir. Kalin/italik varyantlari da yuklenir.
"""
import json
from pathlib import Path

import pymupdf as fitz

# Turkce glifli serif font ailesi (Windows). Yoksa render() daha genel bir alternatife duser.
_FONT_CANDIDATES = {
    "reg": [r"C:\Windows\Fonts\times.ttf", r"C:\Windows\Fonts\georgia.ttf"],
    "bold": [r"C:\Windows\Fonts\timesbd.ttf", r"C:\Windows\Fonts\georgiab.ttf"],
    "italic": [r"C:\Windows\Fonts\timesi.ttf", r"C:\Windows\Fonts\georgiai.ttf"],
    "bolditalic": [r"C:\Windows\Fonts\timesbi.ttf", r"C:\Windows\Fonts\georgiaz.ttf"],
}

# Span flag bitleri (PyMuPDF)
_ITALIC = 1 << 1
_MONO = 1 << 3
_BOLD = 1 << 4

_LABEL_MAX_SIZE = 8.5  # bundan kucuk metin = diyagram etiketi (satir bazinda islenir)


def _resolve_font(kind: str) -> str | None:
    for p in _FONT_CANDIDATES[kind]:
        if Path(p).exists():
            return p
    return None


def _color_rgb(srgb: int) -> tuple[float, float, float]:
    return ((srgb >> 16 & 255) / 255, (srgb >> 8 & 255) / 255, (srgb & 255) / 255)


def _span_style(spans: list[dict]) -> dict:
    """Bir birimdeki span'lardan baskin stili (boyut/kalin/italik/mono/renk) cikarir."""
    big = max(spans, key=lambda s: len(s["text"]))
    size = round(sum(s["size"] * len(s["text"]) for s in spans) / max(sum(len(s["text"]) for s in spans), 1), 1)
    flags = big["flags"]
    return {
        "size": size,
        "bold": bool(flags & _BOLD),
        "italic": bool(flags & _ITALIC),
        "mono": all(s["flags"] & _MONO for s in spans if s["text"].strip()),
        "color": _color_rgb(big.get("color", 0)),
        "font": big["font"],
    }


def _xoverlap(a, b) -> float:
    """iki bbox'in yatay ortusme orani (0..1, kucuk olana gore)."""
    ov = min(a[2], b[2]) - max(a[0], b[0])
    if ov <= 0:
        return 0.0
    return ov / max(min(a[2] - a[0], b[2] - b[0]), 1)


def _cluster_lines(lines: list[dict]) -> list[dict]:
    """Bir blogun satirlarini AYNI mantiksal metne ait olacak sekilde kumeler: dikey komsu
    ve yatay ortusen satirlar tek gruba girer. Boylece cok-satirli bir balon/caption tek
    birim olur (Turkce tum alana yayilir, alt satira tasip cakismaz); uzak etiketler ayrilir."""
    items = [l for l in lines if any(s["text"].strip() for s in l["spans"])]
    items.sort(key=lambda l: (round(l["bbox"][1], 1), l["bbox"][0]))
    groups: list[dict] = []
    for l in items:
        lx0, ly0, lx1, ly1 = l["bbox"]
        lineh = max(ly1 - ly0, 1)
        best = None
        for g in groups:
            gx0, gy0, gx1, gy1 = g["bbox"]
            vgap = ly0 - gy1
            if _xoverlap(l["bbox"], g["bbox"]) > 0.3 and -lineh <= vgap <= 1.7 * lineh:
                best = g
                break
        if best is None:
            groups.append({"lines": [l], "bbox": [lx0, ly0, lx1, ly1]})
        else:
            best["lines"].append(l)
            b = best["bbox"]
            best["bbox"] = [min(b[0], lx0), min(b[1], ly0), max(b[2], lx1), max(b[3], ly1)]
    return groups


def _compatible(g: dict, u: dict) -> bool:
    """u, g grubuna ait mi? Ayni paragraf/balon/caption parcasi olma kosullari (geometrik)."""
    if g["page"] != u["page"] or g["kind"] != u["kind"] or abs(g["size"] - u["size"]) >= 1.5:
        return False
    if _xoverlap(g["bbox"], u["bbox"]) <= 0.6:
        return False
    ax = g["bbox"]; bx = u["bbox"]
    vover = min(ax[3], bx[3]) - max(ax[1], bx[1])  # dikey ortusme
    if vover > 0:  # ust uste binen parcalar (bolunmus caption/justify blok)
        return vover > 0.4 * min(ax[3] - ax[1], bx[3] - bx[1])
    gap = -vover  # dikey bosluk (satir kaydirmasi mi, ayri madde mi?)
    return gap <= 0.3 * u["size"]  # balon devam-satiri ~1, madde bosluklari ~4 -> ayrilir


def _merge_adjacent(units: list[dict]) -> list[dict]:
    """Ayni mantiksal metnin (paragraf/balon/caption) birden cok bloga bolundugu durumlari
    GEOMETRIK olarak birlestirir -- yan yana balonlarda siralama araya girse bile calisir.
    Ayri paragraf/liste-maddesi birlesmez (dikey bosluk esigi)."""
    groups: list[dict] = []
    for u in sorted(units, key=lambda u: (u["page"], round(u["bbox"][1], 1), u["bbox"][0])):
        g = next((g for g in groups if _compatible(g, u)), None)
        if g is None:
            groups.append({**u, "parts": [(u["bbox"], u["text"])]})
        else:
            g["parts"].append((u["bbox"], u["text"]))
            b, ub = g["bbox"], u["bbox"]
            g["bbox"] = [min(b[0], ub[0]), min(b[1], ub[1]), max(b[2], ub[2]), max(b[3], ub[3])]
    out = []
    for g in groups:
        parts = sorted(g["parts"], key=lambda p: (round(p[0][1], 1), p[0][0]))
        g["text"] = " ".join(t for _, t in parts).strip()
        g.pop("parts", None)
        out.append(g)
    return out


def extract_units(pdf_path: str, pages: list[int]) -> list[dict]:
    """Cevrilecek metin birimlerini cikarir. Satirlar mantiksal metne gore kumelenir
    (cok-satirli balon/caption/paragraf tek birim), kod/monospace bloklar atlanir."""
    doc = fitz.open(pdf_path)
    raw: list[dict] = []
    for pno in pages:
        page = doc[pno]
        pw = page.rect.width
        for b in page.get_text("dict")["blocks"]:
            if "lines" not in b:
                continue
            for g in _cluster_lines(b["lines"]):
                spans = [s for l in g["lines"] for s in l["spans"]]
                if not any(s["text"].strip() for s in spans):
                    continue
                st = _span_style(spans)
                if st["mono"]:  # kod blogu -> hic dokunma
                    continue
                txt = " ".join("".join(s["text"] for s in l["spans"]).strip() for l in g["lines"]).strip()
                kind = "label" if st["size"] < _LABEL_MAX_SIZE else "body"
                raw.append(_mk(0, pno, g["bbox"], txt, st, kind, pw))
    doc.close()
    merged = _merge_adjacent(raw)
    for i, u in enumerate(merged):
        u["uid"] = i
    return merged


def _mk(uid, pno, bbox, text, st, kind, page_w) -> dict:
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    centered = abs(cx - page_w / 2) < 24 and (x1 - x0) < page_w * 0.7
    if kind == "label":
        align = "center"
    elif centered and st["size"] >= 13:
        align = "center"  # ortalanmis baslik
    elif st["size"] >= 12 or len((text).split()) < 8:
        align = "left"  # baslik / kisa satir
    else:
        align = "justify"
    return {
        "uid": uid, "page": pno, "bbox": [x0, y0, x1, y1], "kind": kind,
        "align": align, "size": st["size"], "bold": st["bold"], "italic": st["italic"],
        "color": list(st["color"]), "text": text, "text_tr": "",
    }


def _fontkind(bold: bool, italic: bool) -> str:
    if bold and italic:
        return "bolditalic"
    if bold:
        return "bold"
    if italic:
        return "italic"
    return "reg"


_ALIGN = {"left": 0, "center": 1, "right": 2, "justify": 3}


def render(pdf_path: str, units: list[dict], out_path: str, pages: list[int],
           dpi_preview: int | None = None) -> dict:
    """units icindeki text_tr'leri orijinal PDF'e basar. pages: cikti sayfalari (siralari korunur)."""
    doc = fitz.open(pdf_path)
    doc.select(pages)
    remap = {orig: i for i, orig in enumerate(pages)}  # orijinal sayfa no -> secilmis indeks

    # font dosya yollari (insert_textbox'a dogrudan fontfile ile verilir)
    fonts = {k: _resolve_font(k) for k in _FONT_CANDIDATES}
    if not fonts["reg"]:
        raise RuntimeError("Turkce glifli serif font bulunamadi (times.ttf/georgia.ttf).")
    fontnames = {"reg": "trreg", "bold": "trbold", "italic": "trital", "bolditalic": "trbi"}

    by_page: dict[int, list[dict]] = {}
    for u in units:
        if u["page"] in remap and u.get("text_tr", "").strip():
            by_page.setdefault(u["page"], []).append(u)

    overflow = 0
    for orig_pno, us in by_page.items():
        page = doc[remap[orig_pno]]
        tcols = _table_columns(page)  # tablo sutun kutulari (tam hucre genisligi icin)
        # 1) metni kaldir. Iki farkli kaynak tipi var:
        #  (a) VEKTOR/METIN-katmanli sayfa: gorunen metin gercek text; grafik/resim vektor.
        #      Dolgu YOK + resim/line-art korunur (renkli diyagram uzerinde beyaz leke olusmasin).
        #  (b) TARANMIS "sandvic" sayfa: tam-sayfa bir raster goruntu + uzerinde gorunmez OCR
        #      metin katmani. Gorunen Ingilizce GORUNTUNUN icindedir; sadece OCR metnini silmek
        #      onu kaldirmaz (alttaki goruntu kalir -> ust uste binme). Bu sayfalarda cevrilen
        #      metin kutularini BEYAZLA kapatip (fill=(1,1,1)) altindaki goruntu pikselini de
        #      sildirmemiz gerekir; diyagram/kod alanlari redakte edilmedigi icin korunur.
        if _is_scanned_page(page):
            for u in us:
                x0, y0, x1, y1 = u["bbox"]
                pad = fitz.Rect(x0 - 1.2, y0 - 1.2, x1 + 1.2, y1 + 1.2) & page.rect
                page.add_redact_annot(pad, fill=(1, 1, 1))
            page.apply_redactions()  # varsayilan: metni kaldir + kapatilan goruntu pikselini beyazla
        else:
            # Vektor/metin-katmanli sayfa. Cogu birim gercek metindir -> saydam redaksiyon
            # (dolgu YOK, resim/line-art korunur) yeterli. AMA bazi sayfalarda (orn. "This page
            # intentionally left blank" ara sayfalari) gorunen metin aslinda kucuk bir taranmis
            # GORUNTU seridi olarak da gomulmustur; sadece gercek metni silmek onu kaldirmaz.
            # Bu yuzden: bir birim bir raster goruntuyle anlamli olcude ortusuyorsa onu BEYAZLA
            # kapat (goruntu pikselini de sildir); aksi halde saydam birak (renkli vektor
            # diyagram uzerinde beyaz leke olusmasin).
            imgrects = []
            try:
                for im in page.get_images(full=True):
                    imgrects.extend(page.get_image_rects(im[0]))
            except Exception:
                imgrects = []
            def _over_image(bb):
                r = fitz.Rect(bb); ra = r.get_area()
                if ra <= 0:
                    return False
                for ir in imgrects:
                    if (r & ir).get_area() >= 0.30 * ra:
                        return True
                return False
            any_white = False
            for u in us:
                if _over_image(u["bbox"]):
                    x0, y0, x1, y1 = u["bbox"]
                    page.add_redact_annot(fitz.Rect(x0-1.2, y0-1.2, x1+1.2, y1+1.2) & page.rect, fill=(1, 1, 1))
                    any_white = True
                else:
                    page.add_redact_annot(fitz.Rect(u["bbox"]), fill=None)
            # Beyaz-kapatma varsa goruntu piksellerinin silinmesi gerekir (IMAGE_PIXELS);
            # yoksa hic resme dokunma (IMAGE_NONE). Vektor diyagramlar her iki durumda korunur.
            page.apply_redactions(
                images=(fitz.PDF_REDACT_IMAGE_PIXELS if any_white else fitz.PDF_REDACT_IMAGE_NONE),
                graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        # asagi tasabilecek gövde bloklari icin: bir sonraki blogun ustune kadar yer ver
        us_sorted = sorted(us, key=lambda u: u["bbox"][1])
        for i, u in enumerate(us_sorted):
            x0, y0, x1, y1 = u["bbox"]
            col = _in_table_column(u, tcols)
            if col is not None:
                # Tablo hucresi: TAM sutun genisligini kullan (Turkce'ye yer ac, kucul-
                # meyi/hucreler-arasi boyut uyumsuzlugunu onle), altta ayni sutundaki bir
                # sonraki hucreye kadar uzat.
                cx0, cx1, ctop, cbot = col
                below = [v["bbox"][1] for v in us_sorted
                         if v is not u and v["bbox"][1] > y0 + 4 and v["bbox"][0] < cx1 and v["bbox"][2] > cx0]
                bottom = (min(below) - 2) if below else min(cbot - 2, y1 + 60)
                rect = fitz.Rect(cx0 + 3, y0 - 1, cx1 - 3, max(bottom, y1))
            else:
                bottom = y1
                if u["kind"] == "body":
                    # Asagi dogru uzatma sinirini, GECERLI birimin USTUNDEN asagida baslayan
                    # (y0 > bu.y0) ve yatayda ortusen herhangi bir birimin ustune kadar kis.
                    # ">y1" degil ">y0" onemli: taranmis sayfalarda OCR kutulari bazen dikeyde
                    # ust uste biner (orn. dipnot, govde paragrafinin bbox alt kenarindan biraz
                    # yukarida baslar); ">y1" kullanmak boyle bir dipnotu "asagidaki blok"
                    # saymaz, govde metni de onun uzerine tasardi. Bu kapatma tasmayi onler
                    # (sigmazsa _fit fontu kucultur).
                    below = [v["bbox"][1] for v in us_sorted
                             if v is not u and v["bbox"][1] > y0 + 4
                             and v["bbox"][0] < x1 and v["bbox"][2] > x0]
                    limit = min(below) - 2 if below else y1 + 90
                    bottom = min(max(y1, limit), page.rect.height - 40)
                rect = fitz.Rect(x0, y0 - 1, x1 + 1, bottom)
            # gecersiz/bos kutulari onar (dar tablo sutunu, sifir-genislikli etiket vb.)
            rect = rect & page.rect
            if rect.width < 2 or rect.height < 2:
                rect = fitz.Rect(x0, y0 - 1, max(x1, x0 + 4), max(y1, y0 + max(u["size"], 6))) & page.rect
            if rect.is_empty or rect.width < 1 or rect.height < 1:
                continue  # onarilamaz derecede kucuk -> atla (nadir)
            if not _fit(page, rect, u, fontnames, fonts):
                overflow += 1

    doc.save(out_path, garbage=4, deflate=True)
    previews = []
    if dpi_preview:
        d2 = fitz.open(out_path)
        base = str(Path(out_path).with_suffix(""))
        for i in range(len(d2)):
            pp = f"{base}_p{i}.png"
            d2[i].get_pixmap(dpi=dpi_preview).save(pp)
            previews.append(pp)
        d2.close()
    doc.close()
    return {"out": out_path, "pages": len(pages), "overflow_units": overflow, "previews": previews}


def _is_scanned_page(page) -> bool:
    """Sayfa bir 'taranmis sandvic' mi? (tam-sayfa raster goruntu + gorunmez OCR metni).
    Boyle sayfalarda gorunen metin GORUNTUNUN icindedir; redaksiyonu beyaz dolguyla yapip
    altindaki goruntu pikselini de silmemiz gerekir. Sayfa alaninin >=%60'ini kaplayan tek
    bir raster goruntu varsa taranmis kabul ederiz."""
    pr = page.rect
    parea = pr.width * pr.height
    if parea <= 0:
        return False
    try:
        for im in page.get_images(full=True):
            for r in page.get_image_rects(im[0]):
                if (r.width * r.height) >= 0.60 * parea:
                    return True
    except Exception:
        return False
    return False


def _table_columns(page) -> list[tuple]:
    """Sayfadaki tablolarin sutun kutularini dondurur: (x0, x1, tablo_ust, tablo_alt).
    find_tables satir sinirlarinda guvenilmez olabilir ama SUTUN sinirlari saglamdir;
    tablo hucrelerinde tam sutun genisligini kullanmak icin bunu kullaniyoruz."""
    cols = []
    try:
        tf = page.find_tables()
    except Exception:
        return cols
    for t in tf.tables:
        cells = [c for c in t.cells if c]
        if not cells:
            continue
        xs = sorted({round(c[0], 1) for c in cells} | {round(c[2], 1) for c in cells})
        tb = t.bbox
        for i in range(len(xs) - 1):
            cols.append((xs[i], xs[i + 1], tb[1], tb[3]))
    return cols


def _in_table_column(u, tcols):
    """u bir tablo sutunu icindeyse (x0, x1, ust, alt) dondurur, degilse None."""
    b = u["bbox"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    for x0, x1, top, bot in tcols:
        if x0 - 2 <= cx <= x1 + 2 and top - 2 <= cy <= bot + 2:
            return (x0, x1, top, bot)
    return None


def _fit(page, rect, u, fontnames, fonts) -> bool:
    """text_tr'yi rect'e basar; sigmazsa fontu kademeli kucultur. True=sigdi."""
    fk = _fontkind(u["bold"], u["italic"])
    if not fonts.get(fk):  # istenen varyant yoksa duz'e dus
        fk = "reg"
    fname, ffile = fontnames[fk], fonts[fk]
    align = _ALIGN[u["align"]]
    color = tuple(u["color"]) if any(u["color"]) else (0, 0, 0)
    size = u["size"]
    minsz = 5.5 if u["kind"] == "body" else 3.5
    while size >= minsz:
        rc = page.insert_textbox(rect, u["text_tr"], fontname=fname, fontfile=ffile,
                                 fontsize=size, align=align, color=color)
        if rc >= 0:
            return True
        size -= 0.2
    page.insert_textbox(rect, u["text_tr"], fontname=fname, fontfile=ffile,
                        fontsize=minsz, align=align, color=color)
    return False


# ---- CLI ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["extract", "render"])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="orn. 38-49 ya da 3,5,7")
    ap.add_argument("--units", help="extract: yazilacak JSON; render: okunacak JSON")
    ap.add_argument("--out", help="render: cikti PDF")
    ap.add_argument("--preview-dpi", type=int)
    a = ap.parse_args()

    def parse_pages(s):
        out = []
        for part in s.split(","):
            if "-" in part:
                lo, hi = part.split("-"); out.extend(range(int(lo), int(hi) + 1))
            else:
                out.append(int(part))
        return out

    pages = parse_pages(a.pages)
    if a.mode == "extract":
        units = extract_units(a.pdf, pages)
        Path(a.units).write_text(json.dumps(units, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"units": len(units), "path": a.units, "pages": pages}, ensure_ascii=False))
    else:
        units = json.loads(Path(a.units).read_text(encoding="utf-8"))
        res = render(a.pdf, units, a.out, pages, dpi_preview=a.preview_dpi)
        print(json.dumps(res, ensure_ascii=False))
