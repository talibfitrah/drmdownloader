"""Config persistence in %APPDATA%/SeenShowDL/config.json."""

import json
import logging
import os
from pathlib import Path

try:
    import keyring
except ImportError:
    keyring = None

logger = logging.getLogger(__name__)

SERVICE_NAME = "SeenShowDL"


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

        # Migrate legacy base64 password to keyring
        self._migrate_legacy_password()

        # Apply defaults for missing keys
        for k, v in _DEFAULTS.items():
            self._data.setdefault(k, v)

        # Log unknown keys but do not delete them
        unknown = [k for k in self._data if k not in _DEFAULTS]
        if unknown:
            logger.info("Config contains unknown keys (kept): %s", unknown)

    def _migrate_legacy_password(self):
        """Migrate base64-encoded password from config file to keyring."""
        import base64
        pw_b64 = self._data.get("password_b64", "")
        username = self._data.get("username", "")
        if pw_b64 and username and keyring:
            try:
                pw = base64.b64decode(pw_b64).decode("utf-8")
                keyring.set_password(SERVICE_NAME, username, pw)
                del self._data["password_b64"]
                self.save()
                logger.info("Migrated legacy password to OS keyring")
            except Exception:
                logger.warning("Failed to migrate legacy password to keyring")

    def save(self):
        try:
            CONFIG_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8"
            )
        except (OSError, PermissionError) as e:
            logger.error("Failed to save config to %s: %s", CONFIG_FILE, e)
            raise OSError(f"Cannot save config: {e}") from e

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        if key not in _DEFAULTS:
            raise ValueError(f"Unknown config key: {key!r}")
        self._data[key] = value
        self.save()

    # ── Credential helpers ─────────────────────────────────────────────

    def get_credentials(self) -> tuple[str, str]:
        user = self._data.get("username", "")
        pw = ""
        if user and keyring:
            try:
                pw = keyring.get_password(SERVICE_NAME, user) or ""
            except Exception:
                logger.warning("Failed to retrieve password from keyring")
                pw = ""
        return user, pw

    def save_credentials(self, username: str, password: str) -> bool:
        self._data["username"] = username
        if keyring is None:
            logger.warning("Keyring not available — password cannot be persisted")
            self.save()
            return False
        try:
            keyring.set_password(SERVICE_NAME, username, password)
        except Exception as e:
            logger.warning("Failed to store password in keyring: %s", e)
            self.save()
            return False
        self.save()
        return True

    def clear_credentials(self):
        username = self._data.get("username", "")
        if username and keyring:
            try:
                keyring.delete_password(SERVICE_NAME, username)
            except Exception:
                pass
        self._data["username"] = ""
        self.save()
