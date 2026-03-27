"""Config persistence in %APPDATA%/SeenShowDL/config.json."""

import base64
import json
import os
from pathlib import Path


def _app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    d = base / "SeenShowDL"
    d.mkdir(parents=True, exist_ok=True)
    return d


APP_DATA_DIR = _app_data_dir()
CONFIG_FILE = APP_DATA_DIR / "config.json"
LOG_DIR = APP_DATA_DIR / "logs"

_DEFAULTS = {
    "username": "",
    "password_b64": "",
    "remember_credentials": True,
    "output_dir": str(Path.home() / "Downloads" / "SeenShow"),
    "language": "en",
}


class Config:
    """Simple JSON config stored in %APPDATA%/SeenShowDL/config.json."""

    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                self._data = json.loads(CONFIG_FILE.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        # Apply defaults for missing keys
        for k, v in _DEFAULTS.items():
            self._data.setdefault(k, v)
        # Remove stale keys from prior versions
        stale = [k for k in self._data if k not in _DEFAULTS]
        for k in stale:
            del self._data[k]

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8"
        )

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    # ── Credential helpers ─────────────────────────────────────────────

    def get_credentials(self) -> tuple[str, str]:
        user = self._data.get("username", "")
        pw_b64 = self._data.get("password_b64", "")
        pw = ""
        if pw_b64:
            try:
                pw = base64.b64decode(pw_b64).decode("utf-8")
            except Exception:
                pw = ""
        return user, pw

    def save_credentials(self, username: str, password: str):
        self._data["username"] = username
        self._data["password_b64"] = base64.b64encode(
            password.encode("utf-8")
        ).decode("ascii")
        self.save()

    def clear_credentials(self):
        self._data["username"] = ""
        self._data["password_b64"] = ""
        self.save()
