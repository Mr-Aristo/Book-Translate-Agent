---
name: kitap-sohbet
description: Cevrilmis (ya da cevrilmekte olan) bir kitap uzerine Turkce SOHBET/TARTISMA yurutur -- bir bolumun ozetini/ana fikrini cikarma, zor bir pasaji acikca aciklama, temalari/argumani konusma, karakterleri/kavramlari tartisma, "bu bolum ne anlatiyor / yazar ne demek istiyor" sorularini metne dayali yanitlama. Kullanici bir kitabi anlamak/konusmak/tartismak isteyince OTOMATIK, ya da `/kitap-sohbet` ile MANUEL cagrilir. Ceviri motoru DEGILDIR; var olan ceviriyi (books/<slug>/ veya ceviriler/) okuyup uzerine konusur.
---

Kullanim: `/kitap-sohbet "<slug | kitap basligi>"` (opsiyonel olarak konu/soru de eklenebilir:
`/kitap-sohbet "hamlet" 3. perde neyi anlatiyor`). Argumansiz da cagrilabilir.

**Otomatik tetikleme:** Kullanici cevrilmis bir kitap hakkinda "su bolumu acikla", "ana fikri ne",
"yazar burada ne demek istiyor", "X bolumunu konusalim/tartisalim", "ozetler misin", "bu kavram ne"
gibi bir sey isterse bu skill devreye girer.

Bu bir **okuma arkadasi/tartisma** araci -- ceviri YAPMAZ (o `translate-book`/`turkce-soyle`/
`translate-pdf-inplace` isi). Amac: kullanicinin kitabi anlamasina, baglam kurmasina, uzerine
dusunmesine yardim etmek. Her sey **metne dayali** olmali; uydurma/genel-kultur atmaca YOK.

## Adimlar

1. **Kitabi belirle.** Argumandan slug ya da baslik al.
   - Eslesme belirsizse mevcut kitaplari listele: `books/*/progress.json` dosyalarini oku
     (her birinde `title`, `slug`, `status`, `translated_chunks/total_chunks` var) ve
     `ceviriler/*.md` ciktilariyla birlikte kullaniciya kisa bir liste sun, hangisini
     konusmak istedigini sor. (Tek kitap varsa dogrudan onu al.)
2. **Ceviri kaynagini bul** (oncelik sirasiyla):
   - Markdown yolu: `ceviriler/<Baslik>.md` (kullaniciya gorunen yayinlanan surum) ya da
     `books/<slug>/book.md` (ic tam kopya). Ikisi de ayni icerik; hangisi varsa.
   - Yerinde-ceviri yolu (PDF): metin `books/<slug>/inplace/pages_tr/*.json` dosyalarinin
     `text_tr` alanlarindadir (sayfa sirasiyla). Tartisma icin bu Turkce metni oku (PDF'i degil).
   - **Kismi ceviri de olur:** sadece cevrilmis kismi tartis; kullanicinin sordugu yer henuz
     cevrilmemisse acikca soyle ("kitabin su anki cevirisi %X'te, o bolum henuz cevrilmedi").
   - Ceviri hic yoksa ama kaynak varsa (`books/<slug>/raw/` ya da `source.*`), kaynaktan da
     konusabilirsin; ama once "ceviri henuz yok, kaynaktan konusuyorum" diye belirt.
3. **Ne konusulacagini anla:** ana fikir/ozet mi, belirli bir bolum/perde/kısım mi, zor bir
   pasajin aciklamasi mi, tema/argüman/karakter tartismasi mi, tek bir kavram mi, yoksa serbest
   soru-cevap mi.
4. **Ilgili metni getir (butun kitabi kore okumadan):**
   - **Belirli bolum/kısım:** `Grep` ile baslik satirlarini (`^#`/`^##`, "Bolum", "Chapter",
     "Perde", numaralar) bul, o bolumun araligini `Read` ile oku (offset/limit ile). Sadece
     gereken kismi baglama al.
   - **Butun kitabin ana fikri/temalari:** once basliklarin listesini cikar (Grep `^#{1,3} `) ki
     kitabin iskeleti/akisi gorunsun; sonra kilit bolumleri (giris, sonuc, doruk bolumler) oku.
     Kitap cok buyukse (birkac yuz KB+) tek tek her seyi baglama sokma -- gerekiyorsa
     `general-purpose` bir alt-agent'a "su dosyayi oku, ana fikri/temalari/bolum ozetlerini
     Turkce cikar" gorevini verip damitilmis sonucu al.
5. **Turkce, metne dayali TARTIS.** Once kisa ve net cevap/ozet ver, sonra derinlestir:
   - **Ana fikir/ozet** isteniyorsa: yazarin ne demek istedigini, bolumun kitabin butunundeki
     yerini, ana savi/donum noktasini acikla. Gerekirse kisa alinti ver ("kitapta soyle geciyor: ...").
   - **Zor pasaj** isteniyorsa: dusuk-jargonlu, gunluk Turkce'yle "yani sunu diyor" seklinde acikla;
     gerekirse ornekle/benzetmeyle. (Kullanicinin "context kurmak zor" dedigi noktada tam da bu skill
     yardim eder.)
   - **Tema/karakter/kavram** isteniyorsa: metindeki dayanaklariyla (nerede geciyor) tartis,
     baglantilari kur (su bolumdeki su, oteki bolumdeki suyla su yuzden iliskili).
   - Yorum katabilirsin ama **spekulasyonu isaretle** ("metin bunu acikca soylemiyor ama su yonde
     okunabilir"). Metinde OLMAYAN bir seyi varmis gibi ANLATMA. Emin degilsen ilgili yeri tekrar oku.
   - Kullaniciyi dusunmeye itecek 1-2 acik uclu soru sorabilirsin (sokratik), ama once sorusunu yanitla.
6. **Sohbeti surdur.** Kullanici ayni kitap uzerinde devam ettikce baglami koru; yeni bolum/konu
   sordukca adim 4-5'i tekrarla. Baska kitaba gecmek isterse adim 1'e don.

## Notlar

- Bu tamamen kullanicinin KENDI kitabini anlamasina yonelik kisisel bir okuma-arkadasi islevidir.
- **Spoiler:** kullanici "bolum bolum ilerliyorum, ilerisini soyleme" derse, sordugu noktanin
  otesine gecen olay orgusunu acma.
- Kaynak dildeki bir ifadeye/kelime oyununa referans gerekiyorsa `books/<slug>/raw/` (markdown yolu)
  ya da orijinal metinden bakabilirsin -- ama tartisma dili Turkce.
- Ceviri kalitesiyle ilgili bir sey fark edilirse (eksik/yanlis/tuhaf cumle), kullaniciya soyle;
  duzeltme ceviri skill'lerinin isidir, bu skill metni degistirmez.
