# Book Transate Agent

Bu proje bagimsizdir (WO/vibecode oyun repo'suyla ilgisi yok). Amac: kullanicinin sahip oldugu
PDF/EPUB kitaplari, kesintiye dayanikli sekilde parca parca Turkce'ye cevirip tek bir Markdown
dosyasinda tutmak, istenirse kitap gorunumlu PDF'e cevirmek.

## Bilesenler

- **Agent** [`.claude/agents/book-translator.md`](.claude/agents/book-translator.md) — ceviri isini yapan asil agent. Her cagrildiginda `next_batch.py`'nin verdigi kadar parcayi cevirir, `finish_batch.py` ile kapatir, sonra durur. Index/tarih/JSON hesabi yapmaz -- hepsi scriptlerde.
- **Skill** [`.claude/skills/translate-book/SKILL.md`](.claude/skills/translate-book/SKILL.md) — kullanici arayuzu: `/translate-book "<dosya yolu>"`. Ilk cagrida kurulum (extraction+chunking) yapar, sonraki cagrilarda kaldigi yerden devam ettirir. Kaynak diyagram-agirlikli metin-katmanli bir PDF ise (pdf_profile.py) OTOMATIK olarak asagidaki yerinde-ceviri yoluna devreder (markdown'i zorlamak icin `--markdown`).
- **Agent** [`.claude/agents/pdf-inplace-translator.md`](.claude/agents/pdf-inplace-translator.md) — YERINDE ceviri icin cevirmen. Bir batch'lik birim-JSON'un `text_tr` alanlarini doldurur (kutuya sigmasi icin ozlu, jargon/kod korunur). translate-pdf-inplace tarafindan cagirilir.
- **Skill** [`.claude/skills/translate-pdf-inplace/SKILL.md`](.claude/skills/translate-pdf-inplace/SKILL.md) — `/translate-pdf-inplace "<dosya yolu>"`. YERINDE (layout-preserving) PDF cevirisi: kaynagin diyagram/renk/duzenini KORUR, sadece metni Turkce ile degistirir. Diyagram/tablo agirlikli teknik kitaplar icin. Kurulum + pdf-inplace-translator'i batch batch cagirma + kismi/tam PDF render. Kesintiye dayanikli.
- **Skill** [`.claude/skills/book-to-pdf/SKILL.md`](.claude/skills/book-to-pdf/SKILL.md) — `/book-to-pdf <slug>`, cevrilmis (tam ya da kismi) `çeviriler/<Baslik>.md`'yi PDF'e basar (Calibre uzerinden, hicbir arayuz acilmadan). (Kendi md->pdf uygulamani kullanacaksan buna gerek yok, `ceviriler/<Baslik>.md` zaten dogrudan girdi olarak kullanilabilir.)
- **Skill** [`.claude/skills/book-to-epub/SKILL.md`](.claude/skills/book-to-epub/SKILL.md) — `/book-to-epub <slug>`, ayni sey ama `.epub` cikti.
- **Scripts** [`scripts/`](scripts/) — `bookutils.py` (tum bookkeeping: slugify, progress, batch hesabi, assemble+resim yayinlama), `extract_book.py` (kurulum/chunking; metin-katmanli PDF'lerde resim/diyagram cikarma dahil, taranmis sayfada docconv/pdf_to_md.py'nin OCR yoluna deger; "taranmis" karari sayfalarin >%50'si metinsizse verilir), `pdf_profile.py` (kaynak markdown mi yerinde-ceviri mi yoluna uygun -- diyagram-agirlikli metin-katmanli PDF = inplace), `next_batch.py` (sirada hangi chunk'lar var), `finish_batch.py` (progress senkronu + birlestirme), `assemble_book.py` (manuel yeniden-birlestirme), `inplace_book.py` (YERINDE ceviri bookkeeping+orkestrasyon: setup/next/finish/status/render; `books/<slug>/inplace/` altinda pages/ + pages_tr/ ile resumable), `docconv/pdf_inplace.py` (yerinde ceviri MOTORU: blok/satir kumeleme ile birim cikarma, sadece-metin redaksiyonu [vektor grafik/resim/renk KORUNUR], Turkce serif fontla sigdirarak yeniden basma, kod bloklari atlanir, tablolarda tam sutun genisligi), `book_to_pdf.py`/`book_to_epub.py` (docconv/ ile export), `docconv/` (kullanicinin "Pdf convertor" projesinden vendored edilmis donusturuculer — arayuzsuz, dogrudan fonksiyon cagrisi: `md_to_pdf`/`md_to_epub`/`calibre_wrapper` Calibre `ebook-convert` tabanli — kitap-gorunumu icin ekstra ayarlarla (a5, hecele, sayfa no, TOC) BILEREK farklilastirildi + resim gecici HTML'e kopyalanacak sekilde genisletildi —, `pdf_to_md` pymupdf4llm + taranmis sayfalarda Tesseract OCR; kaynak degisirse elle senkron tutulmali — bootstrap.py'nin otomatik kurulum/indirme kismi BILEREK vendored edilmedi).
- **Ic calisma klasoru** [`books/<slug>/`](books/) — her kitap icin: `source.*`, `raw/`, `translated/`, `images/` (cikarilan resim/diyagramlar), `glossary.md`, `progress.json`, `book.md`. Bunlar makine/agent icin; kullanicinin bakmasi gereken yer degil.
- **Nihai cikti** `çeviriler/<Kitap Basligi>.md` (markdown yolu; + resimliyse `<Kitap Basligi>_images/`) YA DA `çeviriler/<Kitap Basligi>.pdf` (yerinde-ceviri yolu; diyagram/duzen korunmus) — kullaniciya gorunen TEK yer. Her batch bittiginde guncellenir (kismi ceviriyken de orada).

## Resumability nasil calisiyor

Ilerleme LLM hafizasinda degil, diskte tutulur: markdown yolunda `translated/000N.md`, yerinde
yolunda `inplace/pages_tr/PPPP.json` dosyalarinin varligi tek gercek kaynak (progress.json'daki
sayac bundan senkronlanir, tersi degil). Oturum kesilse, bilgisayar kapansa, farkli bir Claude
Code sohbeti acilsa bile ayni skill tekrar cagrildiginda tam kaldigi yerden devam eder.

## Kurulum

`README.md`'ye bak.

## Notlar

- Cikti sadece kisisel kullanim icindir; dagitim/yayin amacli degildir.
- Taranmis (goruntu tabanli, metin katmani olmayan) PDF'lerde metin OCR ile cikarilir (Tesseract) ama bu yolda resim/diyagram cikarma desteklenmiyor -- diyagram bilinen sinir.
- **Teknik kitaplarda** (yazilim vb.) `book-translator` yaygin teknik jargonu (thread, deadlock, endpoint...) cevirmez, gerekirse ilk gecistigi yerde parantez ile Turkce karsiligini ekler; kod bloklarina hic dokunmaz; resim yollarini degistirmez, sadece aciklama metnini cevirir.
