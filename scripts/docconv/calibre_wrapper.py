"""Calibre ebook-convert etrafinda ince subprocess sarmalayici.

Vendored: kaynak "C:\\Users\\Emre\\Desktop\\Pdf convertor\\converters\\calibre_wrapper.py"
(kullanicinin kendi projesi). Elle senkron tutulmali -- orijinal degisirse buraya da tasi.

Calibre; PDF/EPUB/HTML arasindaki donusumler icin kullanilan tek harici
bagimliligimiz (https://calibre-ebook.com/download). Kurulumda 'ebook-convert'
komut satirina otomatik eklenir; eklenmemisse yaygin kurulum yollarina bakariz.
"""

import shutil
import subprocess
from pathlib import Path


class CalibreNotFoundError(RuntimeError):
    pass


_COMMON_INSTALL_PATHS = (
    r"C:\Program Files\Calibre2\ebook-convert.exe",
    r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    "/Applications/calibre.app/Contents/MacOS/ebook-convert",
)


def find_ebook_convert() -> str:
    exe = shutil.which("ebook-convert")
    if exe:
        return exe
    for candidate in _COMMON_INSTALL_PATHS:
        if Path(candidate).exists():
            return candidate
    raise CalibreNotFoundError(
        "Calibre bulunamadi. https://calibre-ebook.com/download adresinden kurun; "
        "kurulum sirasinda 'ebook-convert' komutu PATH'e otomatik eklenir."
    )


def convert(input_path: Path, output_path: Path, extra_args: list[str] | None = None) -> None:
    exe = find_ebook_convert()
    cmd = [exe, str(input_path), str(output_path)]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Calibre donusum hatasi:\n{result.stdout}\n{result.stderr}")
