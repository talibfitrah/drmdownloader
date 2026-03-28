# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SeenShow Downloader."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None
project_root = Path(SPECPATH).parent

# Collect all customtkinter data files (themes, assets)
ctk_datas = collect_data_files("customtkinter")

# Force-collect all submodules for packages with deferred/dynamic imports
all_hidden = []
for pkg in ["src", "pywidevine", "yt_dlp", "arabic_reshaper", "bidi"]:
    all_hidden += collect_submodules(pkg)

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root)],
    binaries=[
        (str(project_root / "binaries" / "ffmpeg.exe"), "binaries"),
        (str(project_root / "binaries" / "mp4decrypt.exe"), "binaries"),
    ],
    datas=[
        *ctk_datas,
    ],
    hiddenimports=all_hidden + [
        "customtkinter",
        "packaging",
        "packaging.version",
        "unidecode",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SeenShowDL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,            # Show console for debugging (set False for release)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
