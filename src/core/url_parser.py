import re
from dataclasses import dataclass


@dataclass
class ParsedURL:
    url_type: str  # "episode" or "series"
    media_id: int
    episode_id: int | None = None


EPISODE_RE = re.compile(r"/media/(\d+)/episode/(\d+)")
SERIES_RE = re.compile(r"/media/(\d+)(?:/|$|\?)")


def parse_seenshow_url(url: str) -> ParsedURL:
    """Parse a seenshow.com URL into media/episode IDs."""
    url = url.strip()

    m = EPISODE_RE.search(url)
    if m:
        return ParsedURL("episode", int(m.group(1)), int(m.group(2)))

    m = SERIES_RE.search(url)
    if m:
        return ParsedURL("series", int(m.group(1)))

    raise ValueError(
        "Invalid URL. Expected:\n"
        "  https://seenshow.com/media/1234/episode/5678/play\n"
        "  https://seenshow.com/media/1234"
    )
