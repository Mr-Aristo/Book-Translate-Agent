"""Cevrilmis chunk'lari book.md + ceviriler/<Baslik>.md olarak yeniden uretir (manuel calistirma icin).

Normal akista bunu agent degil finish_batch.py cagirir (progress.json'u da senkronlar).
Bu script sadece dogrudan/manuel yeniden-birlestirme icin var.

Kullanim:
    python assemble_book.py <slug>
"""
import json
import sys

from bookutils import assemble


def main() -> int:
    if len(sys.argv) != 2:
        print("Kullanim: python assemble_book.py <slug>", file=sys.stderr)
        return 1

    result = assemble(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
