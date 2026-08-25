# Book Transate Agent (Antigravity)

Bu, projenin Claude Code (`.claude/`, `CLAUDE.md`) tarafindaki kurulumunun **Antigravity karsiligi**.
Ayni scriptlere (`scripts/`) isaret eder -- Python kodu her iki agent icin de ortak ve degismedi;
sadece agent/workflow TANIMLARININ formati ve klasoru farkli (Antigravity `.agents/` bekler,
`.claude/` degil).

Amac: kullanicinin sahip oldugu PDF/EPUB kitaplari, kesintiye dayanikli sekilde parca parca
Turkce'ye cevirip `çeviriler/<Kitap Basligi>.md` altinda tutmak; istenirse `.pdf`/`.epub` olarak
da disari vermek. Teknik (yazilim vb.) kitaplarda jargon/kod/resim'e ozel dikkat kurallari icin
asagidaki subagent tanimina bak.

## Bilesenler

- **Subagent** [`.agents/agents/book-translator/agent.md`](.agents/agents/book-translator/agent.md) —
  `.claude/agents/book-translator.md` ile AYNI mantik, Antigravity frontmatter'ina (`subagent: true`)
  uyarlanmis. `invoke_subagent` ile cagrilir.
- **Workflow'lar** [`.agents/workflows/`](.agents/workflows/) — `/translate-book`, `/book-to-pdf`,
  `/book-to-epub`. Claude Code tarafindaki `.claude/skills/*/SKILL.md` dosyalarinin birebir
  Antigravity karsiligi (ayni adimlar, ayni script cagrilari).
- **Scripts** [`scripts/`](scripts/) — Claude Code tarafiyla PAYLASILIYOR, degismedi. Detay icin
  `CLAUDE.md`'deki "Bilesenler" bolumune bak (Antigravity'ye ozel bir sey yok, ayni Python).
- **Ic calisma klasoru** `books/<slug>/`, **nihai cikti** `çeviriler/<Kitap Basligi>.md` —
  `CLAUDE.md` ile ayni, degismedi.

## Antigravity'ye ozel notlar

- Custom agent frontmatter alanlari (`subagent`, `model`, `commandExecutionPolicy` vb.) resmi
  Antigravity dokumantasyonundan dogrulandi (2026-08 itibariyle), ama Antigravity hizli gelisen
  bir urun -- kurulumunda bir alan/klasor adi (`.agents/workflows/` vs `.agent/workflows/` gibi
  kucuk farklar goruldu kaynaklar arasinda) tutmazsa Antigravity'nin kendi "Customizations" panelinden
  dogru klasoru kontrol et ve gerekirse tasi.
- `commandExecutionPolicy` BILEREK belirtilmedi (varsayilana birakildi) -- "sandbox" gibi kisitlayici
  bir deger, bu agent'in ihtiyac duydugu serbest Bash/Python calistirmayi (script cagrilari) engelleyebilir.
  Ceviri/export calismiyorsa ilk kontrol edilecek yer burasi.
- Model tier `pro` olarak ayarlandi (Claude Code tarafindaki `model: sonnet` karsiligi, en yetenekli
  tier -- ceviri kalitesi icin onemli, `flash`'a dusurme).

## Resumability ve teknik kitap kurallari

`CLAUDE.md`'deki "Resumability nasil calisiyor" ve "Notlar" bolumleriyle birebir ayni -- ilerleme
diskte (`translated/000N.md` dosyalarinin varligi) tutulur, LLM hafizasinda degil; teknik jargon/kod/
resim kurallari `book-translator` subagent tanimina gomulu.
