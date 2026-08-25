---
description: PDF/EPUB kitabi turkce'ye cevirmeye baslar ya da kaldigi yerden devam ettirir (kurulum + book-translator subagent'ini bir batch icin cagirma + ilerleme raporu).
---

# translate-book

Kullanim: `/translate-book "<kaynak dosya yolu>"` (opsiyonel: `--slug <ad>`, `--all` ile kitap bitene kadar art arda batch'ler).

## Adimlar

1. Argumandan kaynak dosya yolunu al. Yol `.pdf` veya `.epub` degilse kullaniciya sor.
2. Slug belirle: `--slug` verilmisse onu kullan, yoksa dosya adindan turet (bosluklar `-`'ye, Turkce karakterler ASCII'ye — `scripts/bookutils.py:slugify` mantigi).
3. `books/<slug>/progress.json` var mi kontrol et.
   - **Yoksa (ilk kez):** calistir:
     ```
     python "scripts/extract_book.py" "<kaynak dosya yolu>" --slug <slug>
     ```
     Cikan ozet mesajini (kac chunk, kac kelime) kullaniciya aktar. Basarisiz olursa (orn. taranmis/gorsel PDF, OCR gerekiyor) hatayi oldugu gibi ilet, devam etme.
   - **Varsa (devam):** progress.json'u oku, mevcut ilerlemeyi (`translated_chunks/total_chunks`) rapor et.
4. `progress.json.status == "done"` ise: "kitap zaten tamamen cevrilmis, /book-to-pdf <slug> ile PDF'e cevirebilirsin" de ve dur.
5. Batch calistir: `book-translator` subagent'ini `invoke_subagent` ile cagir, promptunda **acik anahtar** olarak sunlari ver: proje kok dizini (mutlak yol), `slug`, "next_batch.py ile bir sonraki batch'i al ve cevir, finish_batch.py ile kapat" talimati. Subagent kendi icinde next_batch/translate/glossary/finish_batch adimlarini yapar; progress.json'a KENDISI elle dokunmaz.
6. Subagent donunce `books/<slug>/progress.json`'u tekrar oku, guncel `translated_chunks/total_chunks` ve yuzdeyi kullaniciya rapor et. Nihai/guncel cevirinin `ceviriler/<Kitap Basligi>.md` altinda oldugunu hatirlat (kismi ceviriyken de orada gorunur, her batch'te guncellenir).
7. **`--all` modu:** adim 5-6'yi `status == "done"` olana kadar ya da guvenlik siniri olan **20 batch**'e ulasana kadar tekrarla; her turda kisa bir ilerleme satiri yaz (spam etme, sadece "X/Y (%Z)"). 20 batch sinirina takilirsa kullaniciya "guvenlik siniri nedeniyle durdum, `/translate-book ... --all` ile devam edebilirsin" de.
8. `status == "done"` olduysa, kullaniciya `/book-to-pdf <slug>` ya da `/book-to-epub <slug>` workflow'unu hatirlat.

## Not: uzun sureli/otonom devam

Kullanici "arka planda kendi kendine devam etsin" derse, bu workflow'u tek basina bir daemon gibi
calistirma — Antigravity'nin arka plan gorev/subagent mekanizmasini kullanmasini oner.
