# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SeenShow Downloader."""

import os
from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH).parent

# Collect customtkinter data files (required)
from PyInstaller.utils.hooks import collect_data_files
ctk_datas = collect_data_files("customtkinter")

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
    hiddenimports=[
        "pywidevine",
        "pywidevine.cdm",
        "pywidevine.device",
        "pywidevine.pssh",
        "pywidevine.license_protocol_pb2",
        "yt_dlp",
        "customtkinter",
        "packaging",
        "packaging.version",
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
    console=True,            # Show console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
