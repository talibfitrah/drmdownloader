import os

__version__ = "1.0.0"
APP_NAME = "SeenShow Downloader"

# Each URL constant can be overridden via the corresponding environment variable.
# Env: SEENSHOW_API_BASE (default: https://api.seenshow.com)
API_BASE = os.environ.get("SEENSHOW_API_BASE", "https://api.seenshow.com")
# Env: SEENSHOW_KEYCLOAK_BASE (default: https://keycloak-prod-v2.seenshow.com)
KEYCLOAK_BASE = os.environ.get("SEENSHOW_KEYCLOAK_BASE", "https://keycloak-prod-v2.seenshow.com")
# Env: SEENSHOW_KEYCLOAK_REALM (default: seen)
KEYCLOAK_REALM = os.environ.get("SEENSHOW_KEYCLOAK_REALM", "seen")
# Env: SEENSHOW_SITE_BASE (default: https://seenshow.com)
SITE_BASE = os.environ.get("SEENSHOW_SITE_BASE", "https://seenshow.com")
# Env: SEENSHOW_WIDEVINE_LICENSE_URL
WIDEVINE_LICENSE_URL = os.environ.get(
    "SEENSHOW_WIDEVINE_LICENSE_URL",
    "https://lic.drmtoday.com/license-proxy-widevine/cenc/?specConform=true",
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

GITHUB_REPO = "talibfitrah/drmdownloader"
