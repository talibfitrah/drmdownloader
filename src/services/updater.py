"""Self-update via GitHub Releases."""

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import requests

from ..core.constants import __version__, GITHUB_REPO


class UpdateStatus(Enum):
    AVAILABLE = "available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"


@dataclass
class UpdateCheckResult:
    status: UpdateStatus
    latest_version: str = ""
    download_url: str = ""
    error_message: str = ""


def check_for_update() -> UpdateCheckResult:
    """Check GitHub for a newer release. Returns a typed result."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=10,
        )
        if resp.status_code == 404:
            return UpdateCheckResult(UpdateStatus.UP_TO_DATE, __version__)
        if resp.status_code != 200:
            return UpdateCheckResult(
                UpdateStatus.ERROR, error_message=f"GitHub API returned {resp.status_code}"
            )

        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")
        if not tag:
            return UpdateCheckResult(UpdateStatus.UP_TO_DATE, __version__)

        from packaging.version import parse
        if parse(tag) <= parse(__version__):
            return UpdateCheckResult(UpdateStatus.UP_TO_DATE, __version__)

        download_url = ""
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            return UpdateCheckResult(
                UpdateStatus.ERROR, tag,
                error_message="New version found but no .exe asset in release.",
            )

        return UpdateCheckResult(UpdateStatus.AVAILABLE, tag, download_url)

    except requests.RequestException as e:
        return UpdateCheckResult(
            UpdateStatus.ERROR, error_message=f"Network error: {e}"
        )
    except Exception as e:
        return UpdateCheckResult(
            UpdateStatus.ERROR, error_message=f"Update check failed: {e}"
        )


def download_update(url: str, progress_cb=None) -> str:
    """Download update exe to temp dir. Returns path to downloaded file."""
    dest = Path(tempfile.gettempdir()) / "SeenShowDL_update.exe"
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if progress_cb and total:
                progress_cb(downloaded / total)

    return str(dest)


def apply_update(new_exe_path: str):
    """Replace current exe with the new one via a helper batch script."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Cannot self-update when running from source.")

    current_exe = sys.executable
    old_exe = current_exe + ".old"

    bat = Path(tempfile.gettempdir()) / "seenshow_update.bat"
    bat.write_text(
        f'@echo off\r\n'
        f'timeout /t 2 /nobreak >nul\r\n'
        f'del "{old_exe}" 2>nul\r\n'
        f'move /y "{current_exe}" "{old_exe}"\r\n'
        f'move /y "{new_exe_path}" "{current_exe}"\r\n'
        f'start "" "{current_exe}"\r\n'
        f'del "%~f0"\r\n',
        encoding="utf-8",
    )
    subprocess.Popen(
        ["cmd", "/c", str(bat)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    sys.exit(0)


def cleanup_old_exe():
    """Delete leftover .old file from a previous update."""
    if getattr(sys, "frozen", False):
        old = Path(sys.executable + ".old")
        if old.exists():
            try:
                old.unlink()
            except OSError:
                pass
