import requests

from .constants import API_BASE, USER_AGENT


class SeenAPI:
    """Interacts with the SeenShow API."""

    def __init__(self, access_token: str):
        self.token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        })

    def get_media_detail(self, media_id: int) -> dict:
        resp = self.session.get(f"{API_BASE}/{media_id}/detail", timeout=30)
        resp.raise_for_status()
        return resp.json()["response"]["data"]

    def get_episode_drm_token(self, episode_id: int) -> dict:
        resp = self.session.post(
            f"{API_BASE}/episodes/{episode_id}/drm-token", timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def find_episode(self, media_detail: dict, episode_id: int) -> dict | None:
        for season in media_detail.get("seasons", []):
            for ep in season.get("episodes", []):
                if ep.get("id") == episode_id:
                    return ep
        return None

    def get_all_episodes(self, media_id: int) -> tuple[str, list[dict]]:
        """Return (media_title, flat list of all episodes across seasons)."""
        media = self.get_media_detail(media_id)
        media_title = media.get("mediaTitle", f"media_{media_id}")
        episodes = []
        for season in sorted(
            media.get("seasons", []),
            key=lambda s: s.get("order", s.get("number", 0)),
        ):
            season_name = season.get("name", "")
            for ep in sorted(
                season.get("episodes", []),
                key=lambda e: e.get("order", 0),
            ):
                ep["_season_name"] = season_name
                ep["_media_title"] = media_title
                episodes.append(ep)
        return media_title, episodes
