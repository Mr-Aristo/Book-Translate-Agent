---
description: Cevrilmis (tam ya da kismi) kitabi kitap gorunumlu PDF'e cevirir, docconv/ (Calibre) uzerinden -- hicbir arayuz acilmaz.
---

# book-to-pdf

Kullanim: `/book-to-pdf <slug>` (ya da `--input <herhangi bir .md>` ile slug disi bir dosya).

## Adimlar

1. Argumandan `slug` al. `çeviriler/<Kitap Basligi>.md` var mi kontrol et (yoksa: "once assemble icin book-translator subagent'i en az bir batch calistirmali" de ve dur — bu dosya sadece cevrilmis chunk varsa olusur).
2. Calistir:
   ```
   python "scripts/book_to_pdf.py" <slug>
   ```
3. Cikti yorumla (JSON):
   - `status: "ok"`: `pdf_path`i kullaniciya bildir (`çeviriler/<Baslik>.pdf`).
   - `status: "fallback_html"`: Calibre bulunamamis demektir. `html_path`i kullaniciya bildir, tarayicidan "PDF olarak yazdir" secenegini soyle; dogrudan PDF icin Calibre kurulumunu oner (https://calibre-ebook.com/download, ~220MB) — bu kurulumu KENDIN calistirma, kullanicinin onayiyla yap.
4. Kitap `progress.json.status != "done"` ise (kismi ceviri), kullaniciya PDF'in su an kismi oldugunu hatirlat.
