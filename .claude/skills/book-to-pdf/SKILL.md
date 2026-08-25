---
name: book-to-pdf
description: Cevrilmis (tam ya da kismi) kitabi kitap gorunumlu bir PDF'e cevirir. "Pdf convertor" projesinden vendored edilen docconv/ paketi uzerinden, Calibre'nin ebook-convert'i ile calisir -- pandoc/LaTeX gerekmez, hicbir arayuz acilmaz.
---

Kullanim: `/book-to-pdf <slug>` (ya da `--input <herhangi bir .md>` ile slug disi bir dosya).

## Adimlar

1. Argumandan `slug` al. `çeviriler/<Kitap Basligi>.md` var mi kontrol et (yoksa: "once assemble icin book-translator agent'i en az bir batch calistirmali" de ve dur — bu dosya sadece cevrilmis chunk varsa olusur).
2. Bash ile calistir:
   ```
   python "scripts/book_to_pdf.py" <slug>
   ```
3. Cikti yorumla (JSON):
   - `status: "ok"`: `pdf_path`i kullaniciya bildir (`çeviriler/<Baslik>.pdf`).
   - `status: "fallback_html"`: Calibre bulunamamis demektir. `html_path`i kullaniciya bildir, tarayicidan "PDF olarak yazdir" secenegini soyle; dogrudan PDF icin Calibre kurulumunu oner (https://calibre-ebook.com/download, ~220MB) — bu kurulumu KENDIN calistirma, kullanicinin onayiyla yap.
4. Kitap `progress.json.status != "done"` ise (kismi ceviri), kullaniciya PDF'in su an kismi oldugunu hatirlat.

## Not

Bu makinede Calibre zaten kurulu (`C:\Program Files\Calibre2\ebook-convert.exe`), yani normalde adim 3'un `fallback_html` dalina hic girilmez.
