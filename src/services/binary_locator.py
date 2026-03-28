import hashlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Expected SHA256 hashes for bundled binaries.
# Update these when upgrading the bundled binary versions.
# Env: SEENSHOW_FFMPEG_SHA256, SEENSHOW_MP4DECRYPT_SHA256
import os

EXPECTED_HASHES: dict[str, str | None] = {
    "ffmpeg": os.environ.get("SEENSHOW_FFMPEG_SHA256"),
    "mp4decrypt": os.environ.get("SEENSHOW_MP4DECRYPT_SHA256"),
}

# Cache verified results per session to avoid repeated hashing
_verified: dict[str, bool] = {}


def _verify_binary(path: str, name: str) -> bool:
    """Verify a binary's SHA256 hash against the expected value.

    Returns True if hash matches or no expected hash is configured.
    Returns False if hash does not match.
    """
    if path in _verified:
        return _verified[path]

    expected = EXPECTED_HASHES.get(name)
    if not expected:
        # No hash configured — skip verification
        _verified[path] = True
        return True

    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual = sha256.hexdigest()
        if actual.lower() == expected.lower():
            _verified[path] = True
            return True
        else:
            logger.error(
                "Binary integrity check failed for %s: expected %s, got %s",
                path, expected, actual,
            )
            _verified[path] = False
            return False
    except OSError as e:
        logger.error("Cannot read binary for verification: %s: %s", path, e)
        _verified[path] = False
        return False


def get_binary(name: str) -> str:
    """Return path to a bundled binary (ffmpeg, mp4decrypt).

    When frozen (PyInstaller), looks in the bundle's binaries/ dir.
    When running from source, looks in the project's binaries/ dir,
    then falls back to PATH (bare name).

    If an expected SHA256 hash is configured, verifies the bundled
    binary before returning it. Falls back to PATH on failure.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "binaries"
    else:
        base = Path(__file__).parent.parent.parent / "binaries"

    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    path = base / exe_name

    if path.exists():
        abs_path = str(path.resolve())
        if _verify_binary(abs_path, name):
            return abs_path
        # Verification failed — fall back to PATH
        logger.warning(
            "Bundled %s failed integrity check, falling back to PATH", name,
        )

    # Fallback: rely on system PATH
    return exe_name if sys.platform == "win32" else name
