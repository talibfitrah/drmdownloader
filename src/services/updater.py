"""Self-update via GitHub Releases with integrity verification."""

import hashlib
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

import requests

from ..core.constants import __version__, GITHUB_REPO

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    AVAILABLE = "available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"


@dataclass
class UpdateCheckResult:
    status: UpdateStatus
    latest_version: str = ""
    download_url: str = ""
    sha256: str = ""
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
        sha256_url = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url")
            if not name or not url:
                continue
            if name.endswith(".exe"):
                download_url = url
            elif name.endswith(".sha256") or name == "checksums.txt":
                sha256_url = url

        if not download_url:
            return UpdateCheckResult(
                UpdateStatus.ERROR, tag,
                error_message="New version found but no .exe asset in release.",
            )

        # Try to fetch expected hash from release
        expected_sha256 = ""
        if sha256_url:
            try:
                hash_resp = requests.get(sha256_url, timeout=10)
                if hash_resp.status_code == 200:
                    # Format: "hash  filename" or just "hash"
                    expected_sha256 = hash_resp.text.strip().split()[0]
            except Exception:
                pass

        return UpdateCheckResult(
            UpdateStatus.AVAILABLE, tag, download_url, expected_sha256,
        )

    except requests.RequestException as e:
        return UpdateCheckResult(
            UpdateStatus.ERROR, error_message=f"Network error: {e}"
        )
    except Exception as e:
        return UpdateCheckResult(
            UpdateStatus.ERROR, error_message=f"Update check failed: {e}"
        )


def download_update(url: str, expected_sha256: str = "", progress_cb=None) -> str:
    """Download update exe to temp dir with integrity verification.

    Returns path to downloaded file. Raises RuntimeError if hash mismatch.
    """
    dest = Path(tempfile.gettempdir()) / "SeenShowDL_update.exe"
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    sha256 = hashlib.sha256()

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            sha256.update(chunk)
            downloaded += len(chunk)
            if progress_cb and total:
                progress_cb(downloaded / total)

    # Verify integrity if we have an expected hash
    if expected_sha256:
        actual = sha256.hexdigest()
        if actual.lower() != expected_sha256.lower():
            try:
                dest.unlink()
            except OSError:
                pass
            raise RuntimeError(
                f"Downloaded file hash mismatch: expected {expected_sha256}, got {actual}. "
                f"Update aborted for security."
            )
        logger.info("Update hash verified: %s", actual)

    return str(dest)


def _batch_escape(path: str) -> str:
    """Escape a path for safe use inside a batch script."""
    path = path.replace("%", "%%")
    for ch in "^&|<>!":
        path = path.replace(ch, f"^{ch}")
    return path


def apply_update(new_exe_path: str):
    """Replace current exe with the new one via a helper batch script."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Cannot self-update when running from source.")

    if not Path(new_exe_path).exists():
        raise FileNotFoundError(
            f"Update file not found: {new_exe_path}. Cannot apply update."
        )

    current_exe = _batch_escape(sys.executable)
    old_exe = _batch_escape(sys.executable + ".old")
    new_exe_path = _batch_escape(new_exe_path)

    bat = Path(tempfile.gettempdir()) / "seenshow_update.bat"
    bat.write_text(
        f'@echo off\r\n'
        f'setlocal DisableDelayedExpansion\r\n'
        f'\r\n'
        f'rem Wait for the current process to release the exe\r\n'
        f'set RETRIES=0\r\n'
        f':waitloop\r\n'
        f'if %RETRIES% GEQ 30 (\r\n'
        f'    echo ERROR: Timed out waiting for SeenShowDL.exe to be released.\r\n'
        f'    pause\r\n'
        f'    exit /b 1\r\n'
        f')\r\n'
        f'2>nul (\r\n'
        f'    >>"{current_exe}" (call )\r\n'
        f') && goto :dostep1\r\n'
        f'set /a RETRIES+=1\r\n'
        f'timeout /t 1 /nobreak >nul\r\n'
        f'goto :waitloop\r\n'
        f'\r\n'
        f':dostep1\r\n'
        f'del "{old_exe}" 2>nul\r\n'
        f'move /y "{current_exe}" "{old_exe}"\r\n'
        f'if errorlevel 1 (\r\n'
        f'    echo ERROR: Failed to back up current executable.\r\n'
        f'    pause\r\n'
        f'    exit /b 1\r\n'
        f')\r\n'
        f'\r\n'
        f'move /y "{new_exe_path}" "{current_exe}"\r\n'
        f'if errorlevel 1 (\r\n'
        f'    echo ERROR: Failed to install new executable. Rolling back...\r\n'
        f'    move /y "{old_exe}" "{current_exe}"\r\n'
        f'    pause\r\n'
        f'    exit /b 1\r\n'
        f')\r\n'
        f'\r\n'
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
