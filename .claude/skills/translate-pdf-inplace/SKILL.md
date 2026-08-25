---
name: translate-pdf-inplace
description: Bir PDF kitabi YERINDE (layout-preserving) Turkce'ye cevirir -- kaynagin diyagramlarini, renklerini, fontlarini ve sayfa duzenini KORUYARAK, yalnizca metni Turkce ile degistirerek. Diyagram/tablo agirlikli TEKNIK kitaplar icin markdown yolundan cok daha sadik. Kesintiye dayaniklidir (disk = tek dogru kaynak). Kurulum + pdf-inplace-translator agent'ini batch batch cagirma + kismi/tam PDF render.
---

# translate-pdf-inplace

Kaynak PDF'in gorsel yapisini bozmadan Turkce'ye cevirir: metin katmanini `pdf_inplace`
motoruyla kaldirir (vektor grafik/resim/renk KORUNUR) ve ayni konuma Turkce'yi basar.
Diyagram-agirlikli teknik kitaplar (mimari semalar, akis diyagramlari, tablolar) icin uygundur.

Sadece **metin katmanli** (taranmis olmayan) PDF'lerde calisir. EPUB veya taranmis PDF icin
markdown yolu (`translate-book`) kullanilir.

## Ne zaman

- Kullanici `/translate-pdf-inplace "<dosya yolu>"` cagirdiginda, VEYA
- `translate-book`, diyagram-agirlikli metin-katmanli bir PDF tespit edip buraya devrettiginde.

## Adimlar

Tum bookkeeping `scripts/inplace_book.py`'de; sen index/tarih/JSON/render hesabi YAPMA.
`<KOK>` = proje kok dizini (bu skill'in iki ust klasoru).

1. **Slug**: dosya adindan uret ya da kullanicinin verdigi slug'i kullan (markdown yoluyla
   ayni kitapsa AYNI slug -- `books/<slug>/` paylasilir). Kaynak PDF `books/<slug>/source.pdf`
   olmali; degilse once oraya kopyala (translate-book kurulumu bunu yapar) ya da dogrudan ver.

2. **Kurulum (idempotent)**:
   `python "<KOK>/scripts/inplace_book.py" setup <slug> [--batch-pages 10]`
   Tum sayfalarin cevrilecek birimlerini `books/<slug>/inplace/pages/`'e cikarir. Zaten kuruluysa
   hicbir sey yapmaz. Cikan JSON'dan `total_pages` / `translatable_units`'i oku.

3. **Batch dongusu** -- `status` "done" olana kadar tekrarla:
   a. `python "<KOK>/scripts/inplace_book.py" next <slug>` -> `status=="done"` ise dongu biter.
      Aksi halde `batch_file` (cevrilecek birimler) ve `batch_tr_file` (yazilacak yol) yollarini oku.
   b. **pdf-inplace-translator** agent'ini cagir; ona `batch_file`, `batch_tr_file` yollarini ve
      (varsa) `books/<slug>/glossary.md` yolunu ver. Agent text_tr'leri doldurup batch_tr_file'a yazar.
   c. `python "<KOK>/scripts/inplace_book.py" finish <slug>` -> batch_tr_file'i sayfalara dagitir
      (pages_tr/PPPP.json), ilerlemeyi gunceller. Ciktidan translated_pages/total_pages'i oku.
   - Uzun kitaplarda bu dongu cok tekrar eder; her batch bagimsiz ve kesintiye dayaniklidir
     (pages_tr/ diskte tutulur, tekrar cagrilinca kaldigi yerden devam).

4. **Render**: `python "<KOK>/scripts/inplace_book.py" render <slug>`
   `ceviriler/<Kitap Basligi>.pdf`'i uretir (kismi ceviride cevrilmemis sayfalar orijinal
   dilinde kalir). Her birkac batch'te bir render edip kullaniciya ara ciktisi gosterebilirsin.

5. Kisa Turkce durum raporu ver: kac/kac sayfa, `ceviriler/...pdf` nerede, tamam mi degil mi.

## Notlar

- Cikti sadece kisisel kullanim icindir.
- Kod bloklari (monospace) cevrilmez, dokunulmaz (motor atlar). Diyagram etiketleri ve gövde
  metni cevrilir; renk/kalinlik/italik korunur.
- Turkce metin uzun oldugundan bazi dar kutularda font otomatik kucultulur; tablolarda tam sutun
  genisligi kullanilir. Cok yogun bazi balon/caption'larda kaynak parcalanmasindan minor akis
  kusurlari olabilir (bilinen sinir).
- Font olarak Turkce glifli serif (Times New Roman / Georgia) gomulur.
