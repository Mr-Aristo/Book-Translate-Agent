---
name: translate-book
description: Bir PDF/EPUB kitabi turkce'ye cevirmeye baslar ya da kaldigi yerden devam ettirir. Kurulum (extraction+chunking) + book-translator agent'ini bir batch icin cagirma + ilerleme raporu.
---

Kullanim: `/translate-book "<kaynak dosya yolu>"` (opsiyonel: `--slug <ad>`, `--all` ile kitap bitene kadar art arda batch'ler, `--markdown` ile diyagram-agirlikli PDF'lerde bile markdown yolunu zorla, `--style canyucel` ile "Can Yucel usulu" ozgur/edebi ceviri).

## Adimlar

0. **Stil secimi.** `--style canyucel` (veya `--canyucel` / `--turkce-soyle`) verilmisse, bu **`turkce-soyle`
   skill'ine devret** (ayni `<kaynak yolu>` / `--slug` / `--all` ile) ve buradan cikma. O yol kitabi
   "Turkce soyleyen" usulu ceviren `canyucel-translator` agent'ini kullanir, sadik moddan AYRI bir
   `books/<slug>-cy/` klasoru ve `ceviriler/<Baslik> (Turkce Soyleyis).md` ciktisi uretir (cakismaz).
   `--style canyucel` verilMEDIYSE varsayilan **sadik mod**dur; asagidan devam et.
1. Argumandan kaynak dosya yolunu al. Yol `.pdf` veya `.epub` degilse kullaniciya sor.
2. Slug belirle: `--slug` verilmisse onu kullan, yoksa dosya adindan turet (bosluklar `-`'ye, Turkce karakterler ASCII'ye — `scripts/bookutils.py:slugify` mantigi).
2.5. **Yol secimi (otomatik).** `--markdown` verilMEDIYSE, kaynagi profille:
   ```
   python "scripts/pdf_profile.py" "<kaynak dosya yolu>"
   ```
   Cikan JSON'daki `recommend == "inplace"` ise (metin-katmanli, diyagram-agirlikli teknik PDF):
   bu markdown yolunu BIRAK ve **`translate-pdf-inplace` skill'ine devret** (ayni `<kaynak yolu>` /
   `--slug` ile) -- yerinde ceviri diyagramlari/duzeni korur, teknik kitaplarda cok daha sadiktir.
   Kullaniciya kisaca "bu kitap diyagram-agirlikli, duzeni koruyan yerinde ceviri yolu kullanilacak"
   de. `recommend == "markdown"` ise (epub/taranmis/roman gibi az-diyagram) asagidan devam et.
   Not: ayni `books/<slug>/` klasoru paylasilir; kaynak PDF `source.pdf` olarak oraya kopyalanmali
   (asagidaki extract_book kurulumu ya da inplace tarafi bunu yapar).
3. `books/<slug>/progress.json` var mi kontrol et (Read/Glob).
   - **Yoksa (ilk kez):** Bash ile calistir:
     ```
     python "scripts/extract_book.py" "<kaynak dosya yolu>" --slug <slug>
     ```
     Cikan ozet mesajini (kac chunk, kac kelime) kullaniciya aktar. Basarisiz olursa (orn. taranmis/gorsel PDF, OCR gerekiyor) hatayi oldugu gibi ilet, devam etme.
   - **Varsa (devam):** progress.json'u oku, mevcut ilerlemeyi (`translated_chunks/total_chunks`) rapor et.
4. `progress.json.status == "done"` ise: "kitap zaten tamamen cevrilmis, /book-to-pdf <slug> ile PDF'e cevirebilirsin" de ve dur.
5. Batch calistir: `book-translator` agent'ini cagir (Agent tool), promptunda **acik anahtar** olarak sunlari ver: proje kok dizini (mutlak yol), `slug`, "next_batch.py ile bir sonraki batch'i al ve cevir, finish_batch.py ile kapat" talimati. Agent kendi icinde next_batch/translate/glossary/finish_batch adimlarini yapar; progress.json'a KENDISI elle dokunmaz.
6. Agent donunce `books/<slug>/progress.json`'u tekrar oku, guncel `translated_chunks/total_chunks` ve yuzdeyi kullaniciya rapor et. Nihai/guncel cevirinin `ceviriler/<Kitap Basligi>.md` altinda oldugunu hatirlat (kismi ceviriyken de orada gorunur, her batch'te guncellenir).
7. **`--all` modu:** adim 5-6'yi `status == "done"` olana kadar ya da guvenlik siniri olan **20 batch**'e ulasana kadar tekrarla; her turda kisa bir ilerleme satiri yaz (spam etme, sadece "X/Y (%Z)"). 20 batch sinirina takilirsa kullaniciya "guvenlik siniri nedeniyle durdum, `/translate-book ... --all` ile devam edebilirsin" de.
8. `status == "done"` olduysa, kullaniciya `/book-to-pdf <slug>` skill'ini hatirlat.

## Not: uzun sureli/otonom devam

Kullanici "arka planda kendi kendine devam etsin" derse, bu skill'i tek basina bir daemon gibi calistirma —
bunun yerine `/loop` skill'ini `/translate-book "<yol>"` promptuyla kurmasini oner (her tetiklenişte bir batch ilerler).
