"""Tests for URL parser — series vs episode vs invalid."""

import pytest
from src.core.url_parser import parse_seenshow_url, ParsedURL


class TestParseSeenshowUrl:
    def test_episode_url_with_play(self):
        r = parse_seenshow_url("https://seenshow.com/media/1981/episode/53142/play")
        assert r == ParsedURL("episode", 1981, 53142)

    def test_episode_url_without_play(self):
        r = parse_seenshow_url("https://seenshow.com/media/1981/episode/53142")
        assert r == ParsedURL("episode", 1981, 53142)

    def test_series_url(self):
        r = parse_seenshow_url("https://seenshow.com/media/1976")
        assert r == ParsedURL("series", 1976, None)

    def test_series_url_trailing_slash(self):
        r = parse_seenshow_url("https://seenshow.com/media/1976/")
        assert r == ParsedURL("series", 1976, None)

    def test_series_url_with_query(self):
        r = parse_seenshow_url("https://seenshow.com/media/2024?tab=episodes")
        assert r == ParsedURL("series", 2024, None)

    def test_whitespace_stripped(self):
        r = parse_seenshow_url("  https://seenshow.com/media/1981/episode/53142/play  ")
        assert r == ParsedURL("episode", 1981, 53142)

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid URL"):
            parse_seenshow_url("https://example.com/foo")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid URL"):
            parse_seenshow_url("")

    def test_no_media_id_raises(self):
        with pytest.raises(ValueError, match="Invalid URL"):
            parse_seenshow_url("https://seenshow.com/media/")
