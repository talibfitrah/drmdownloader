"""Widevine DRM key retrieval via DRMtoday license server."""

import base64
import json
import os
import re
import tempfile
import threading

import requests
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

from .constants import WIDEVINE_LICENSE_URL

PSSH_PATTERN = re.compile(
    r'<ContentProtection\s+schemeIdUri="urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"'
    r'[^>]*>\s*<cenc:pssh>([^<]+)</cenc:pssh>'
)

# CDM device blob — injected at build time via WVD_BLOB env var.
# For local development, set WVD_BLOB in your environment.
_EMBEDDED_WVD = os.environ.get("WVD_BLOB", "")

_device: Device | None = None
_device_lock = threading.Lock()


def _get_device() -> Device:
    """Load the embedded CDM device into memory.

    Writes to a random temp file, loads the Device, then deletes the
    file immediately so no device material persists on disk.
    Uses double-checked locking for thread safety.
    """
    global _device
    if _device is not None:
        return _device

    with _device_lock:
        if _device is not None:
            return _device

        if not _EMBEDDED_WVD:
            raise RuntimeError(
                "CDM device not configured. Set WVD_BLOB environment variable."
            )
        wvd_bytes = base64.b64decode(_EMBEDDED_WVD)
        fd, tmp_path = tempfile.mkstemp(suffix=".wvd")
        try:
            os.write(fd, wvd_bytes)
        finally:
            os.close(fd)
        try:
            _device = Device.load(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return _device


def get_widevine_keys(
    mpd_url: str,
    drm_token: dict,
) -> list[tuple[str, str]]:
    """Get Widevine content keys from DRMtoday license server."""
    mpd_content = requests.get(mpd_url, timeout=30).text

    pssh_match = PSSH_PATTERN.findall(mpd_content)
    if not pssh_match:
        raise RuntimeError("No Widevine PSSH found in MPD manifest")

    pssh = PSSH(pssh_match[0].strip())
    device = _get_device()
    cdm = Cdm.from_device(device)
    session_id = cdm.open()

    try:
        challenge = cdm.get_license_challenge(session_id, pssh)

        custom_data = {
            "userId": drm_token["userId"],
            "sessionId": drm_token["sessionId"],
            "merchant": drm_token["merchant"],
        }

        headers = {
            "x-dt-auth-token": drm_token["upfrontToken"],
            "x-dt-custom-data": base64.b64encode(
                json.dumps(custom_data).encode()
            ).decode(),
            "Content-Type": "application/octet-stream",
        }

        resp = requests.post(
            WIDEVINE_LICENSE_URL, data=challenge, headers=headers, timeout=30
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"License request failed ({resp.status_code}): {resp.text[:300]}"
            )

        cdm.parse_license(session_id, resp.content)

        keys = []
        for key in cdm.get_keys(session_id):
            if key.type == "CONTENT":
                keys.append((key.kid.hex, key.key.hex()))

        if not keys:
            raise RuntimeError("No content keys in license response")

        return keys
    finally:
        cdm.close(session_id)
