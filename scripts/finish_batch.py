"""Bir batch ceviri bittikten sonra bookkeeping'i kapatir: progress.json'u gercek dosya
sayisina gore senkronlar (tarihi de kendisi atar) ve book.md + ceviriler/<Baslik>.md'yi
yeniden uretir.

Kullanim:
    python finish_batch.py <slug>
"""
import json
import sys

from bookutils import assemble, sync_progress


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"status": "error", "message": "kullanim: finish_batch.py <slug>"}))
        return 1

    slug = sys.argv[1]
    progress = sync_progress(slug)
    result = assemble(slug)
    result["slug"] = slug
    result["translated_chunks"] = progress["translated_chunks"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
