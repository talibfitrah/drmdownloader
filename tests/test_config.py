"""Tests for config persistence."""

import json
from unittest.mock import patch

import pytest
from src.services.config import Config, _DEFAULTS


@pytest.fixture
def tmp_config(tmp_path):
    """Patch CONFIG_FILE to use a temp directory."""
    cfg_file = tmp_path / "config.json"
    with patch("src.services.config.CONFIG_FILE", cfg_file):
        yield cfg_file


class TestConfig:
    def test_defaults_applied(self, tmp_config):
        c = Config()
        assert c.get("output_dir") == _DEFAULTS["output_dir"]
        assert c.get("language") == "en"
        assert c.get("username") == ""

    def test_set_and_get(self, tmp_config):
        c = Config()
        c.set("output_dir", "/tmp/test")
        assert c.get("output_dir") == "/tmp/test"
        # Verify persisted
        data = json.loads(tmp_config.read_text("utf-8"))
        assert data["output_dir"] == "/tmp/test"

    def test_save_credentials(self, tmp_config):
        c = Config()
        c.save_credentials("user@test.com", "secret123")
        user, pw = c.get_credentials()
        assert user == "user@test.com"
        assert pw == "secret123"

    def test_clear_credentials(self, tmp_config):
        c = Config()
        c.save_credentials("user@test.com", "secret123")
        c.clear_credentials()
        user, pw = c.get_credentials()
        assert user == ""
        assert pw == ""

    def test_load_existing(self, tmp_config):
        tmp_config.write_text(json.dumps({
            "username": "existing@test.com",
            "output_dir": "/custom/path",
        }))
        c = Config()
        assert c.get("username") == "existing@test.com"
        assert c.get("output_dir") == "/custom/path"
        # Defaults for missing keys
        assert c.get("language") == "en"

    def test_stale_keys_removed(self, tmp_config):
        tmp_config.write_text(json.dumps({
            "wvd_path": "/old/path.wvd",
            "auto_update": True,
            "username": "user",
        }))
        c = Config()
        assert c.get("wvd_path") is None
        assert c.get("auto_update") is None
        assert c.get("username") == "user"

    def test_corrupt_file_handled(self, tmp_config):
        tmp_config.write_text("not valid json{{{")
        c = Config()
        # Should load defaults without crashing
        assert c.get("language") == "en"

    def test_password_base64_corrupt(self, tmp_config):
        tmp_config.write_text(json.dumps({"password_b64": "!!!invalid!!!"}))
        c = Config()
        _, pw = c.get_credentials()
        assert pw == ""
