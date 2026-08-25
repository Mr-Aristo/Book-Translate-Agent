---
description: Cevrilmis (tam ya da kismi) kitabi .epub'a cevirir, docconv/ (Calibre) uzerinden -- hicbir arayuz acilmaz. book-to-pdf'in epub karsiligi.
---

# book-to-epub

Kullanim: `/book-to-epub <slug>` (ya da `--input <herhangi bir .md>` ile slug disi bir dosya).

## Adimlar

1. Argumandan `slug` al. `çeviriler/<Kitap Basligi>.md` var mi kontrol et (yoksa: "once assemble icin book-translator subagent'i en az bir batch calistirmali" de ve dur).
2. Calistir:
   ```
   python "scripts/book_to_epub.py" <slug>
   ```
3. Cikti yorumla (JSON):
   - `status: "ok"`: `epub_path`i kullaniciya bildir (`çeviriler/<Baslik>.epub`).
   - `status: "error"` (Calibre bulunamadi): kullaniciya Calibre kurulumunu oner (https://calibre-ebook.com/download, ~220MB) — bu kurulumu KENDIN calistirma, kullanicinin onayiyla yap. PDF'in aksine epub icin HTML fallback anlamli degil (cikti tanim geregi .epub olmali), bu yuzden burada duruyoruz.
4. Kitap `progress.json.status != "done"` ise (kismi ceviri), kullaniciya epub'un su an kismi oldugunu hatirlat.
