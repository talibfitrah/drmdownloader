"""Tests for updater — tri-state results."""

from unittest.mock import patch, MagicMock

from src.services.updater import check_for_update, UpdateStatus
from src.core.constants import __version__


class TestCheckForUpdate:
    def test_newer_version_available(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v99.0.0",
            "assets": [{"name": "SeenShowDL.exe", "browser_download_url": "https://example.com/dl.exe"}],
        }
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.AVAILABLE
        assert result.latest_version == "99.0.0"
        assert result.download_url == "https://example.com/dl.exe"

    def test_same_version_is_up_to_date(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": f"v{__version__}",
            "assets": [],
        }
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_older_version_is_up_to_date(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v0.0.1", "assets": []}
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_404_is_up_to_date(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_api_error_returns_error_not_up_to_date(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.ERROR
        assert "500" in result.error_message

    def test_network_error_returns_error(self):
        import requests
        with patch("src.services.updater.requests.get", side_effect=requests.ConnectionError("offline")):
            result = check_for_update()
        assert result.status == UpdateStatus.ERROR
        assert "Network error" in result.error_message

    def test_newer_version_without_exe_asset_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v99.0.0",
            "assets": [{"name": "source.tar.gz", "browser_download_url": "https://example.com/src.tar.gz"}],
        }
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.ERROR
        assert "no .exe" in result.error_message.lower()

    def test_malformed_json_returns_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("bad json")
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.ERROR

    def test_malformed_asset_skipped(self):
        """Assets missing name or URL are safely skipped."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v99.0.0",
            "assets": [
                {},  # missing both name and url
                {"name": "SeenShowDL.exe"},  # missing url
                {"name": "SeenShowDL.exe", "browser_download_url": "https://example.com/dl.exe"},
            ],
        }
        with patch("src.services.updater.requests.get", return_value=mock_resp):
            result = check_for_update()
        assert result.status == UpdateStatus.AVAILABLE
        assert result.download_url == "https://example.com/dl.exe"
