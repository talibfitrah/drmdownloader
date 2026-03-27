"""SeenShow Keycloak OAuth PKCE authentication."""

import re
from typing import Callable

import requests

from .constants import SITE_BASE, USER_AGENT


class AuthenticationError(Exception):
    pass


class SeenAuth:
    """Handles the full Keycloak OAuth PKCE flow via NextAuth."""

    def __init__(self, username: str, password: str,
                 on_status: Callable[[str], None] | None = None):
        self.username = username
        self.password = password
        self._status = on_status or (lambda _: None)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.access_token: str | None = None

    def authenticate(self) -> str:
        """Run the full OAuth flow and return the access token.

        Status callbacks receive i18n keys: auth_csrf, auth_keycloak,
        auth_login_page, auth_signing_in, auth_completing, auth_success.
        """
        self._status("auth_csrf")
        try:
            resp = self.session.get(
                f"{SITE_BASE}/api/auth/csrf", timeout=30
            )
            resp.raise_for_status()
            csrf = resp.json()["csrfToken"]
        except (requests.RequestException, KeyError, ValueError) as e:
            raise AuthenticationError(f"Cannot reach SeenShow servers: {e}")

        self._status("auth_keycloak")
        try:
            resp = self.session.post(
                f"{SITE_BASE}/api/auth/signin/keycloak",
                data={"csrfToken": csrf, "callbackUrl": SITE_BASE},
                allow_redirects=False,
                timeout=30,
            )
        except requests.RequestException as e:
            raise AuthenticationError(f"Cannot reach authentication server: {e}")
        keycloak_url = resp.headers.get("Location")
        if not keycloak_url:
            raise AuthenticationError("No redirect to Keycloak. Site may be down.")

        self._status("auth_login_page")
        try:
            login_page = self.session.get(keycloak_url, timeout=30).text
        except requests.RequestException as e:
            raise AuthenticationError(f"Cannot load login page: {e}")
        match = re.search(r'"loginAction":\s*"([^"]+)"', login_page)
        if not match:
            raise AuthenticationError(
                "Could not find login form. Site layout may have changed."
            )
        login_action = match.group(1)

        self._status("auth_signing_in")
        try:
            resp = self.session.post(
                login_action,
                data={"username": self.username, "password": self.password},
                allow_redirects=False,
                timeout=30,
            )
        except requests.RequestException as e:
            raise AuthenticationError(f"Login request failed: {e}")
        if resp.status_code != 302:
            raise AuthenticationError("Invalid email or password.")
        callback_url = resp.headers["Location"]

        self._status("auth_completing")
        try:
            self.session.get(callback_url, allow_redirects=True, timeout=30)
        except requests.RequestException as e:
            raise AuthenticationError(f"Token exchange failed: {e}")

        try:
            session_data = self.session.get(
                f"{SITE_BASE}/api/auth/session", timeout=30
            ).json()
        except (requests.RequestException, ValueError) as e:
            raise AuthenticationError(f"Cannot retrieve session: {e}")

        self.access_token = session_data.get("accessToken")
        if not self.access_token:
            raise AuthenticationError(
                "Authentication completed but no token received."
            )

        self._status("auth_success")
        return self.access_token
