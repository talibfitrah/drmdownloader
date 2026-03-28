# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SeenShow Downloader."""

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = Path(SPECPATH).parent

# Collect customtkinter data files (themes, assets)
ctk_datas = collect_data_files("customtkinter")

# Force-collect submodules for packages with complex imports
hidden = []
for pkg in ["pywidevine", "yt_dlp", "arabic_reshaper", "bidi", "construct"]:
    try:
        hidden += collect_submodules(pkg)
    except Exception:
        pass

# Explicitly list ALL src modules (can't use collect_submodules on local packages)
src_modules = [
    "src", "src.core", "src.services", "src.ui", "src.app",
    "src.core.constants", "src.core.auth", "src.core.api",
    "src.core.drm", "src.core.downloader", "src.core.url_parser",
    "src.services.config", "src.services.binary_locator",
    "src.services.download_manager", "src.services.updater",
    "src.ui.theme", "src.ui.i18n", "src.ui.main_window",
    "src.ui.login_frame", "src.ui.download_frame", "src.ui.settings_frame",
    "src.main",
]

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
    hiddenimports=hidden + src_modules + [
        "customtkinter",
        "packaging",
        "packaging.version",
        "unidecode",
        "Crypto",
        "Crypto.Cipher",
        "Crypto.Cipher.AES",
        "Crypto.Hash",
        "Crypto.Util",
        "google.protobuf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(project_root / "build" / "runtime_hook.py")],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
