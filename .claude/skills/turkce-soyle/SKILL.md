---
name: turkce-soyle
description: Bir edebi PDF/EPUB kitabi (siir, roman, oyun) "Can Yucel usulu" TURKCE'ye soyler ya da kaldigi yerden devam ettirir. Kelimeye degil metnin canina sadik, yerlilestiren, konusma dilinde, sesi/ritmi Turkce'de yeniden kuran OZGUR ceviri. Sadik moddan (translate-book) AYRI bir cikti uretir, cakismaz. Kurulum + canyucel-translator agent'ini batch batch cagirma + ilerleme raporu. Kesintiye dayanikli.
---

Kullanim: `/turkce-soyle "<kaynak dosya yolu>"` (opsiyonel: `--slug <ad>`, `--all` ile kitap bitene kadar art arda batch'ler).

Bu skill, kitabi **Can Yucel usulu** ("Turkce soyleyen") cevirir: kelimeye degil metnin canina
sadik, yerlilestiren, konusma dilinde, sesi/ritmi Turkce'de yeniden kuran OZGUR bir ceviri.
**Edebi eserler icindir** (siir/roman/oyun) -- teknik/diyagram-agirlikli kitaplar icin DEGILDIR
(onlar icin `/translate-book` sadik mod ya da `/translate-pdf-inplace` yerinde ceviri).

Sadik `translate-book` yolundan tamamen AYRI calisir: kendi `books/<slug>-cy/` klasoru ve kendi
`ceviriler/<Baslik> (Turkce Soyleyis).md` ciktisi vardir; ikisi ayni kitapta yan yana durabilir,
CAKISMAZ.

## Adimlar

1. Argumandan kaynak dosya yolunu al. Yol `.pdf` veya `.epub` degilse kullaniciya sor.
2. **Taban slug** belirle: `--slug` verilmisse onu kullan, yoksa dosya adindan turet
   (`scripts/bookutils.py:slugify` mantigi). Sonra Can Yucel yolunun slug'i = **taban + "-cy"**
   (orn. `hamlet` -> `hamlet-cy`). Boylece sadik modun `books/hamlet/`'inden ayri, kendi
   `books/hamlet-cy/` klasorunde resumable calisir.
   - **Baslik** = kaynak dosya adi (uzantisiz) + ` (Turkce Soyleyis)`. Yayinlanan cikti bu baslikla
     olur, sadik modun ciktisiyla cakismaz.
3. `books/<slug>-cy/progress.json` var mi kontrol et (Read/Glob).
   - **Yoksa (ilk kez):** Bash ile calistir (edebi ceviri daha yogun oldugu icin daha kucuk,
     sik-checkpoint'li batch'ler):
     ```
     python "scripts/extract_book.py" "<kaynak dosya yolu>" --slug <taban>-cy --title "<dosya adi> (Turkce Soyleyis)" --chunk-words 1500 --batch-size 3
     ```
     Cikan ozet mesajini (kac chunk, kac kelime) kullaniciya aktar. Basarisiz olursa (orn.
     taranmis/gorsel PDF, OCR gerekiyor) hatayi oldugu gibi ilet, devam etme.
   - **Varsa (devam):** progress.json'u oku, mevcut ilerlemeyi (`translated_chunks/total_chunks`) rapor et.
4. `progress.json.status == "done"` ise: "kitap zaten tamamen Turkce'ye soylenmis, `/book-to-pdf <taban>-cy`
   ile PDF'e / `/book-to-epub <taban>-cy` ile epub'a cevirebilirsin" de ve dur.
5. Batch calistir: **`canyucel-translator`** agent'ini cagir (Agent tool). Promptunda **acik anahtar**
   olarak sunlari ver: proje kok dizini (mutlak yol), `slug` (= `<taban>-cy`), "next_batch.py ile bir
   sonraki batch'i al ve Can Yucel usulu Turkce SOYLE, finish_batch.py ile kapat" talimati. Agent
   kendi icinde next_batch/soyle/glossary/finish_batch adimlarini yapar; progress.json'a KENDISI
   elle dokunmaz.
   (Sakin `book-translator` agent'ini cagirma -- o sadik/teknik moddur; bu skill Can Yucel usulu icin
   `canyucel-translator`'i cagirir.)
6. Agent donunce `books/<slug>-cy/progress.json`'u tekrar oku, guncel `translated_chunks/total_chunks`
   ve yuzdeyi rapor et. Guncel cevirinin `ceviriler/<Baslik> (Turkce Soyleyis).md` altinda oldugunu
   hatirlat (kismi ceviriyken de orada gorunur, her batch'te guncellenir).
7. **`--all` modu:** adim 5-6'yi `status == "done"` olana kadar ya da guvenlik siniri **20 batch**'e
   ulasana kadar tekrarla; her turda kisa bir ilerleme satiri yaz ("X/Y (%Z)", spam etme). 20 batch
   sinirina takilirsa "guvenlik siniri nedeniyle durdum, `/turkce-soyle ... --all` ile devam
   edebilirsin" de.
8. `status == "done"` olduysa `/book-to-pdf <taban>-cy` (ya da `/book-to-epub <taban>-cy`) skill'ini hatirlat.

## Not: uzun sureli/otonom devam

Kullanici "arka planda kendi kendine devam etsin" derse, bu skill'i tek basina daemon gibi
calistirma -- bunun yerine `/loop` skill'ini `/turkce-soyle "<yol>"` promptuyla kurmasini oner
(her tetiklenişte bir batch ilerler).
