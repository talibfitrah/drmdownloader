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

# Embedded Widevine L3 CDM device (base64-encoded .wvd).
# Loaded into memory once, temp file deleted immediately after.
_EMBEDDED_WVD = (
    "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"
    "4U5DMZUvwPZBaLgCAPL+2zOLuuoTkIqkapJWljUeLD5dVV6l0atnqdCRtQMCoVQ6uYWDfU7rNmnR"
    "mS/mn4SoJsGUtIDb2SDnXJcVteH5zhcOwzyKRHEkNbSuraxexRWM3dnYO1z6mwug3gm2u5rckNwkc"
    "+4Kj2gFe8lLJjJjz8zY71Cm6qlmS3Ph7I41HQWmE3VeR65rXhdJqDFtNuIvlSzR/ze1wg2r1/CDR"
    "NXDtAEGqP1lNE2ds6D7h4vZ+KIeg39NNSLBh1cPZ2NRaO4SEvjlm8EOOun1CShM8KLjBmdmuQ8gM"
    "+NMBbrVPAZMUNL0A3KTkE/1Y/I1B1/lPf1q5uphmVFKozf2HGKZ0artN15hGAm8+0Ds17u5vYb7h"
    "ZWDC55lFB1ABcIInu0ra9KSJRyBTrRDUcXc6hxY+bPw+UU7rZCBtqGF8AfodEI5x0K3kVtRXf/rG"
    "hYKDGNvbXBhbnlfbmFtZRIGR29vZ2xlGiEKCm1vZGVsX25hbWUSE3Nka19ncGhvbmU2NF94ODZfNj"
    "QaGwoRYXJjaGl0ZWN0dXJlX25hbWUSBng4Nl82NBoWCgtkZXZpY2VfbmFtZRIHZW11NjR4YRojCg"
    "xwcm9kdWN0X25hbWUSE3Nka19ncGhvbmU2NF94ODZfNjQaYgoKYnVpbGRfaW5mbxJUZ29vZ2xlL3"
    "Nka19ncGhvbmU2NF94ODZfNjQvZW11NjR4YToxNi9CRTJBLjI1MDUzMC4wMjYuRjMvMTM4OTQzMj"
    "M6dXNlcmRlYnVnL2Rldi1rZXlzGi4KFHdpZGV2aW5lX2NkbV92ZXJzaW9uEhYxOS41LjBAQlYx"
    "QS4yNTAyMjYuMDAxGiQKH29lbV9jcnlwdG9fc2VjdXJpdHlfcGF0Y2hfbGV2ZWwSATAa7wMKHG9l"
    "bV9jcnlwdG9fYnVpbGRfaW5mb3JtYXRpb24SzgN7CiJzb2NfdmVuZG9yIjogIldpZGV2aW5lIi"
    "wKInNvY19tb2RlbCI6ICJTb2Z0d2FyZSIsCiJ0YV92ZXIiOiAiTi9BIiwKInVzZXNfb3BrIjogZm"
    "Fsc2UsCiJ0ZWVfb3MiOiAiTi9BIiwKInRlZV9vc192ZXIiOiAiTi9BIiwKImlzX2RlYnVnIjogZm"
    "Fsc2UsCiJnaXRfY29tbWl0IjogIiIsCiJidWlsZF90aW1lc3RhbXAiOiAiRmViIDI1IDIwMjUgMD"
    "A6MTg6MDciLAoibW9kZSI6ICJIQVlTVEFDS19PTkxZIiwKInJpa2VycyI6IHt9LAoiaGF5c3RhY2"
    "siOiB7InNvY192ZW5kb3IiOiJMM18zMzEwMCIsInNvY19tb2RlbCI6Ilg4NiA2NCBiaXQiLCJ0YV"
    "92ZXIiOiIxOC4xLjArTWF5IDE0IDIwMjRfMTk6MDQ6NDJfIiwidXNlc19vcGsiOmZhbHNlLCJ0ZW"
    "Vfb3MiOiJub25lIiwidGVlX29zX3ZlciI6IjAuMC4wIiwiZm9ybV9mYWN0b3IiOiJMMyIsImltcG"
    "xlbWVudGVyIjoiV2lkZXZpbmUiLCJmdXNlZCI6ZmFsc2V9Cn0yFggBEAEgACgSMABAAEgAUAFYAG"
    "ABcAE="
)

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
