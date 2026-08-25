# Book Transate Agent

PDF/EPUB kitaplari yavas ve sistemli sekilde Turkce'ye ceviren, kesintiye dayanikli
(kaldigi yerden devam eden) bir Claude Code agent + skill kurulumu.

## Nasil calisir (ozet)

1. `/translate-book "<kitap.pdf|kitap.epub>"` — kitabi parcalara boler, ilk batch'i cevirir.
2. Ayni komutu tekrar cagirdikca (ilerleme diskte tutulur) kitap bitene kadar devam eder.
   `--all` ile tek oturumda arka arkaya batch'ler (guvenlik siniri: 20 batch/cagri).
3. Guncel ceviri (tam ya da kismi, her batch'te guncellenir) `çeviriler/<Kitap Basligi>.md`
   altinda hazir bekler — kendi md->pdf uygulamana dogrudan bunu verebilirsin.
4. Istersen `/book-to-pdf <slug>` ile de kitap gorunumlu PDF cikarabilirsin (opsiyonel, Calibre gerektirir — bu makinede zaten kurulu).

Detayli mimari icin [`CLAUDE.md`](CLAUDE.md).

## Kurulum

### 1. Python bagimliliklari

```
pip install -r requirements.txt
```

(Bu makinede Python 3.12 zaten kurulu bulundu.)

### 2. PDF ciktisi icin (opsiyonel — kendi md->pdf uygulamani kullanmiyorsan)

`book-to-pdf` skill'i `scripts/docconv/` altindaki (kullanicinin "Pdf convertor" projesinden
vendored edilmis) donusturucuyu kullanir — bu, Calibre'nin `ebook-convert` komutuna dayanir,
pandoc/LaTeX GEREKMEZ:

```
# https://calibre-ebook.com/download -- ~220MB
```

**Bu makinede Calibre zaten kurulu** (`C:\Program Files\Calibre2\ebook-convert.exe`), yani
ekstra kuruluma gerek yok. Calibre kurulu degilse skill otomatik olarak "tarayicidan yazdir"
icin HTML uretir.

### 3. Taranmis (goruntu tabanli) PDF'ler icin OCR (opsiyonel)

`extract_book.py` da ayni `scripts/docconv/` paketini kullanir (`pdf_to_md.py`) — metin katmani
olan sayfalarda pymupdf4llm, metin katmani OLMAYAN (taranmis) sayfalarda otomatik olarak
Tesseract OCR'a duser (karisik PDF'lerde bile calisir, sayfa sayfa karar verir):

```
# https://github.com/UB-Mannheim/tesseract/wiki -- ~50MB, kurulumda "Turkish" dil paketini sec
```

**Bu makinede Tesseract da zaten kurulu** (`C:\Program Files\Tesseract-OCR\tesseract.exe`).
Kurulu degilse, taranmis sayfalar icin extraction hata verir (duz metin PDF'ler yine calisir).

## Kullanim ornekleri

```
/translate-book "C:\Users\Emre\Desktop\C# okunacak kitaplar\Build yourself\The Psychology of Money - Morgan Housel.pdf"
/translate-book "C:\Users\Emre\Desktop\C# okunacak kitaplar\Build yourself\Lives of the Stoics The Art of Living from Zeno to Marcus Aurelius Ryan Holiday.epub" --all
/book-to-pdf the-psychology-of-money-morgan-housel   # opsiyonel, kendi md->pdf uygulamani kullanmiyorsan
```

Kesintisiz otonom devam istiyorsan (orn. arkada calissin, sen baska is yap):

```
/loop /translate-book "<ayni dosya yolu>"
```

`/loop`, her tetiklenişte bir batch ilerletip bir sonraki cagriyi kendi kendine planlar.

## Klasor yapisi

```
Book Transate Agent/
  .claude/agents/book-translator.md      - ceviriyi yapan agent
  .claude/skills/translate-book/         - /translate-book
  .claude/skills/book-to-pdf/            - /book-to-pdf (opsiyonel)
  scripts/                               - bookutils, extraction, batch hesabi, assemble, pdf export
    docconv/                             - "Pdf convertor" projesinden vendored (Calibre md->pdf/epub, Tesseract OCR pdf->md)
  çeviriler/<Kitap Basligi>.md           - NIHAI cikti, buraya bakman yeterli (her batch'te guncellenir)
  çeviriler/<Kitap Basligi>.pdf          - (book-to-pdf sonrasi, opsiyonel)
  books/<slug>/                          - ic calisma klasoru (elle karisma)
    source.pdf|epub                      - orijinalin kopyasi
    raw/000N.md                          - kaynak parcalar (cevrilecek)
    translated/000N.md                   - cevrilmis parcalar (gercek ilerleme kaynagi)
    glossary.md                          - terim sozlugu (tutarlilik icin)
    progress.json                        - ilerleme durumu (next_batch.py/finish_batch.py yazar)
    book.md                              - ic calisma kopyasi (çeviriler/'dekiyle ayni icerik)
```

## Bilinen sinirlar

- **Taranmis/goruntu-tabanli PDF sayfalari** Tesseract OCR ile okunuyor (bkz. Kurulum #3) —
  ama OCR kalitesi kaynak goruntunun cozunurluguyle sinirli, kusursuz degil. Tesseract kurulu
  degilse bu sayfalarda extraction hata verir.
- **EPUB'daki gorseller** cevrilmiyor/tasinmiyor (sadece metin cikariliyor). Resimli kitaplar icin
  sonradan elle ekleme gerekebilir.
- Ceviri kalitesi chunk sinirlarinda (paragraf/baslik bazli bolundugu icin) genelde sorunsuz,
  ama cok uzun tek cumleler bir chunk sinirina denk gelirse baglam kaybi riski vardir —
  chunk boyutu `extract_book.py --chunk-words` ile ayarlanabilir (varsayilan 2000 kelime).
