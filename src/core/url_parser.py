import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class ParsedURL:
    url_type: str  # "episode" or "series"
    media_id: int
    episode_id: int | None = None


EPISODE_RE = re.compile(r"/media/(\d+)/episode/(\d+)")
SERIES_RE = re.compile(r"/media/(\d+)(?:/(?!episode|settings|edit).*)?(?:\?.*)?$")

ALLOWED_HOSTS = {"seenshow.com", "www.seenshow.com"}


def parse_seenshow_url(url: str) -> ParsedURL:
    """Parse a seenshow.com URL into media/episode IDs."""
    url = url.strip()

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(
            "Invalid URL. Expected a seenshow.com URL:\n"
            "  https://seenshow.com/media/1234/episode/5678/play\n"
            "  https://seenshow.com/media/1234"
        )

    path = parsed.path
    qs = f"?{parsed.query}" if parsed.query else ""
    full = path + qs

    m = EPISODE_RE.search(full)
    if m:
        return ParsedURL("episode", int(m.group(1)), int(m.group(2)))

    m = SERIES_RE.search(full)
    if m:
        return ParsedURL("series", int(m.group(1)))

    raise ValueError(
        "Invalid URL. Expected:\n"
        "  https://seenshow.com/media/1234/episode/5678/play\n"
        "  https://seenshow.com/media/1234"
    )
