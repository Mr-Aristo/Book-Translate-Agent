"""Bir sonraki cevrilecek batch'i hesaplar ve JSON olarak yazdirir.

Agent bunu cagirir ve donen "batch" listesindeki raw_path/translated_path'leri
OLDUGU GIBI kullanir -- kendisi index/dolgu hesabi yapmaz.

Kullanim:
    python next_batch.py <slug>

Cikti (stdout, JSON):
    {"status": "not_started"}                                   - kurulum yapilmamis
    {"status": "done", ...}                                     - kitap tamamlanmis
    {"status": "in_progress", "batch": [{"index", "raw_path", "translated_path"}, ...]}
"""
import json
import sys

from bookutils import compute_next_batch


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "message": "kullanim: next_batch.py <slug>"}))
        return 1
    print(json.dumps(compute_next_batch(sys.argv[1]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
