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
import tempfile
import zipfile
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
BINARIES_DIR = PROJECT_ROOT / "binaries"
DIST_DIR = PROJECT_ROOT / "dist"
WORK_DIR = PROJECT_ROOT / "build" / "pyinstaller"

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
BENTO4_URL = "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-microsoft-win32.zip"


def download_file(url: str, dest: Path):
    """Download a file with streaming, timeouts, and atomic write."""
    print(f"  Downloading {url}")
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dest.parent, suffix=".tmp")
    fd_owned = False
    try:
        resp = requests.get(url, stream=True, timeout=(30, 300))
        resp.raise_for_status()
        with os.fdopen(tmp_fd, "wb") as f:
            fd_owned = True
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        shutil.move(tmp_path, dest)
    except requests.RequestException as e:
        if not fd_owned:
            os.close(tmp_fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise RuntimeError(f"Download failed for {url}: {e}") from e


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


def smoke_test_imports():
    """Verify the critical frozen-build imports resolve before packaging."""
    print("\n[check] Verifying critical imports...")
    code = (
        "import importlib, sys; "
        f"sys.path.insert(0, {str(PROJECT_ROOT)!r}); "
        "importlib.import_module('src.core.drm'); "
        "importlib.import_module('src.core.downloader')"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        check=True,
    )
    print("[ok] Critical imports resolved")


def clean_build_dirs():
    """Remove stale PyInstaller outputs so analysis is always fresh."""
    for path in [DIST_DIR, WORK_DIR]:
        if path.exists():
            print(f"[clean] Removing {path.relative_to(PROJECT_ROOT)}")
            shutil.rmtree(path)


def run_pyinstaller():
    print("\n[build] Running PyInstaller...")
    spec = PROJECT_ROOT / "build" / "seenshow_dl.spec"
    clean_build_dirs()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec),
            "--noconfirm",
            "--clean",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(WORK_DIR),
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )
    print(f"\n[done] Build complete. Output in {DIST_DIR}")


def main():
    if platform.system() != "Windows":
        print("WARNING: This build script targets Windows.")
        print("         Cross-compilation is not supported by PyInstaller.")
        print("         The build will proceed but the exe won't run on this OS.\n")

    BINARIES_DIR.mkdir(exist_ok=True)
    ensure_ffmpeg()
    ensure_mp4decrypt()
    smoke_test_imports()
    run_pyinstaller()


if __name__ == "__main__":
    main()
