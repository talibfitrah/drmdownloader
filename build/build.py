#!/usr/bin/env python3
"""
Build script for SeenShow Downloader.

Run on Windows:
    python build/build.py

This will:
1. Download ffmpeg and mp4decrypt Windows binaries if missing
2. Run PyInstaller to produce the .exe
"""

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BINARIES_DIR = PROJECT_ROOT / "binaries"

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
BENTO4_URL = "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-microsoft-win32.zip"


def download_file(url: str, dest: Path):
    print(f"  Downloading {url}")
    urllib.request.urlretrieve(url, dest)


def ensure_ffmpeg():
    target = BINARIES_DIR / "ffmpeg.exe"
    if target.exists():
        print("[ok] ffmpeg.exe already present")
        return

    print("[dl] Downloading ffmpeg...")
    zip_path = BINARIES_DIR / "ffmpeg.zip"
    download_file(FFMPEG_URL, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.filename.endswith("ffmpeg.exe"):
                info.filename = "ffmpeg.exe"
                zf.extract(info, BINARIES_DIR)
                break
    zip_path.unlink()
    print("[ok] ffmpeg.exe extracted")


def ensure_mp4decrypt():
    target = BINARIES_DIR / "mp4decrypt.exe"
    if target.exists():
        print("[ok] mp4decrypt.exe already present")
        return

    print("[dl] Downloading Bento4 (mp4decrypt)...")
    zip_path = BINARIES_DIR / "bento4.zip"
    download_file(BENTO4_URL, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.filename.endswith("mp4decrypt.exe"):
                info.filename = "mp4decrypt.exe"
                zf.extract(info, BINARIES_DIR)
                break
    zip_path.unlink()
    print("[ok] mp4decrypt.exe extracted")


def run_pyinstaller():
    print("\n[build] Running PyInstaller...")
    spec = PROJECT_ROOT / "build" / "seenshow_dl.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"],
        cwd=str(PROJECT_ROOT),
        check=True,
    )
    print("\n[done] Build complete. Output in dist/SeenShowDL/")


def main():
    if platform.system() != "Windows":
        print("WARNING: This build script targets Windows.")
        print("         Cross-compilation is not supported by PyInstaller.")
        print("         The build will proceed but the exe won't run on this OS.\n")

    BINARIES_DIR.mkdir(exist_ok=True)
    ensure_ffmpeg()
    ensure_mp4decrypt()
    run_pyinstaller()


if __name__ == "__main__":
    main()
