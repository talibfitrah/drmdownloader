import sys
from pathlib import Path


def get_binary(name: str) -> str:
    """Return path to a bundled binary (ffmpeg, mp4decrypt).

    When frozen (PyInstaller), looks in the bundle's binaries/ dir.
    When running from source, looks in the project's binaries/ dir,
    then falls back to PATH (bare name).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "binaries"
    else:
        base = Path(__file__).parent.parent.parent / "binaries"

    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    path = base / exe_name
    if path.exists():
        return str(path)

    # Fallback: rely on system PATH
    return exe_name if sys.platform == "win32" else name
