"""Tests for config persistence."""

import json
from unittest.mock import patch, MagicMock

import pytest
from src.services.config import Config, _DEFAULTS


@pytest.fixture
def tmp_config(tmp_path):
    """Patch CONFIG_FILE to use a temp directory."""
    cfg_file = tmp_path / "config.json"
    with patch("src.services.config.CONFIG_FILE", cfg_file):
        yield cfg_file


@pytest.fixture
def mock_keyring():
    """Mock keyring for credential tests."""
    store = {}
    mock_kr = MagicMock()
    mock_kr.get_password = lambda svc, user: store.get((svc, user))
    mock_kr.set_password = lambda svc, user, pw: store.update({(svc, user): pw})
    mock_kr.delete_password = lambda svc, user: store.pop((svc, user), None)
    with patch("src.services.config.keyring", mock_kr):
        yield mock_kr


class TestConfig:
    def test_defaults_applied(self, tmp_config, mock_keyring):
        c = Config()
        assert c.get("output_dir") == _DEFAULTS["output_dir"]
        assert c.get("language") == "en"
        assert c.get("username") == ""

    def test_set_and_get(self, tmp_config, mock_keyring):
        c = Config()
        c.set("output_dir", "/tmp/test")
        assert c.get("output_dir") == "/tmp/test"
        # Verify persisted
        data = json.loads(tmp_config.read_text("utf-8"))
        assert data["output_dir"] == "/tmp/test"

    def test_set_unknown_key_raises(self, tmp_config, mock_keyring):
        c = Config()
        with pytest.raises(ValueError, match="Unknown config key"):
            c.set("nonexistent_key", "value")

    def test_save_credentials(self, tmp_config, mock_keyring):
        c = Config()
        c.save_credentials("user@test.com", "secret123")
        user, pw = c.get_credentials()
        assert user == "user@test.com"
        assert pw == "secret123"

    def test_clear_credentials(self, tmp_config, mock_keyring):
        c = Config()
        c.save_credentials("user@test.com", "secret123")
        c.clear_credentials()
        user, pw = c.get_credentials()
        assert user == ""
        assert pw == ""

    def test_load_existing(self, tmp_config, mock_keyring):
        tmp_config.write_text(json.dumps({
            "username": "existing@test.com",
            "output_dir": "/custom/path",
        }))
        c = Config()
        assert c.get("username") == "existing@test.com"
        assert c.get("output_dir") == "/custom/path"
        # Defaults for missing keys
        assert c.get("language") == "en"

    def test_unknown_keys_kept(self, tmp_config, mock_keyring):
        """Unknown keys are logged but not deleted."""
        tmp_config.write_text(json.dumps({
            "future_feature": True,
            "username": "user",
        }))
        c = Config()
        # Unknown key should still be accessible via raw _data
        assert c._data.get("future_feature") is True
        assert c.get("username") == "user"

    def test_corrupt_file_handled(self, tmp_config, mock_keyring):
        tmp_config.write_text("not valid json{{{")
        c = Config()
        # Should load defaults without crashing
        assert c.get("language") == "en"

    def test_keyring_failure_returns_empty_password(self, tmp_config):
        """If keyring is unavailable, get_credentials returns empty password."""
        with patch("src.services.config.keyring", None):
            c = Config()
            c._data["username"] = "user@test.com"
            _, pw = c.get_credentials()
            assert pw == ""

    def test_legacy_password_migration(self, tmp_config, mock_keyring):
        """Legacy base64 passwords are migrated to keyring on load."""
        import base64
        pw_b64 = base64.b64encode(b"oldpassword").decode()
        tmp_config.write_text(json.dumps({
            "username": "user@test.com",
            "password_b64": pw_b64,
        }))
        c = Config()
        user, pw = c.get_credentials()
        assert user == "user@test.com"
        assert pw == "oldpassword"
        # password_b64 should be removed from file after migration
        data = json.loads(tmp_config.read_text("utf-8"))
        assert "password_b64" not in data
