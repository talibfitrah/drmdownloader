"""Tests for downloader — cancellation, cleanup, result types."""

import pytest
from src.core.downloader import (
    safe_filename,
    DownloadResult,
    DownloadCancelled,
    _check_cancel,
)


class TestSafeFilename:
    def test_basic(self):
        assert safe_filename("Show", "Episode 1") == "Show - Episode 1"

    def test_strips_illegal_chars(self):
        result = safe_filename('Show: "The Best"', "Ep<1>")
        assert ":" not in result
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_collapses_whitespace(self):
        result = safe_filename("Show   Name", "  Episode   1  ")
        assert "   " not in result

    def test_arabic(self):
        result = safe_filename("وادي ميسان", "الحلقة 13")
        assert "وادي ميسان" in result
        assert "الحلقة 13" in result


class TestCheckCancel:
    def test_no_cancel_check(self):
        _check_cancel(None)  # Should not raise

    def test_cancel_not_set(self):
        _check_cancel(lambda: False)  # Should not raise

    def test_cancel_set_raises(self):
        with pytest.raises(DownloadCancelled):
            _check_cancel(lambda: True)


class TestDownloadResult:
    def test_success(self):
        r = DownloadResult(True, "/path/file.mp4")
        assert r.success
        assert not r.cancelled

    def test_failure(self):
        r = DownloadResult(False, error="DRM failed")
        assert not r.success
        assert not r.cancelled

    def test_cancelled(self):
        r = DownloadResult(False, error="Cancelled", cancelled=True)
        assert not r.success
        assert r.cancelled
