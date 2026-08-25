---
name: book-to-epub
description: Cevrilmis (tam ya da kismi) kitabi .epub'a cevirir. "Pdf convertor" projesinden vendored edilen docconv/ paketi uzerinden, Calibre'nin ebook-convert'i ile calisir -- hicbir arayuz acilmaz. book-to-pdf'in epub karsiligi.
---

Kullanim: `/book-to-epub <slug>` (ya da `--input <herhangi bir .md>` ile slug disi bir dosya).

## Adimlar

1. Argumandan `slug` al. `çeviriler/<Kitap Basligi>.md` var mi kontrol et (yoksa: "once assemble icin book-translator agent'i en az bir batch calistirmali" de ve dur).
2. Bash ile calistir:
   ```
   python "scripts/book_to_epub.py" <slug>
   ```
3. Cikti yorumla (JSON):
   - `status: "ok"`: `epub_path`i kullaniciya bildir (`çeviriler/<Baslik>.epub`).
   - `status: "error"` (Calibre bulunamadi): kullaniciya Calibre kurulumunu oner (https://calibre-ebook.com/download, ~220MB) — bu kurulumu KENDIN calistirma, kullanicinin onayiyla yap. PDF'in aksine epub icin HTML fallback anlamli degil (cikti tanim geregi .epub olmali), bu yuzden burada duruyoruz.
4. Kitap `progress.json.status != "done"` ise (kismi ceviri), kullaniciya epub'un su an kismi oldugunu hatirlat.

## Not

Bu makinede Calibre zaten kurulu (`C:\Program Files\Calibre2\ebook-convert.exe`), yani normalde adim 3'un hata dalina hic girilmez.
