"""Download pipeline: fetch, download, decrypt, mux."""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yt_dlp

from ..services.binary_locator import get_binary
from .drm import get_widevine_keys

# Progress callback signature: (phase_key: str, pct: float, extra: dict)
# phase_key is an i18n key; extra may contain speed, eta_secs, etc.
ProgressCb = Callable[[str, float, dict], None] | None
CancelCheck = Callable[[], bool] | None

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Maximum filename length (excluding extension) to avoid OS limits
_MAX_FILENAME_LEN = 200


class DownloadCancelled(Exception):
    pass


@dataclass
class DownloadResult:
    success: bool
    output_path: str = ""
    error: str = ""
    cancelled: bool = False


def safe_filename(media_title: str, ep_name: str) -> str:
    # Transliterate Arabic/Unicode to ASCII for max compatibility with
    # external tools (mp4decrypt, ffmpeg) on Windows
    try:
        from unidecode import unidecode
        name = unidecode(f"{media_title} - {ep_name}")
    except ImportError:
        name = f"{media_title} - {ep_name}"
    name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    name = re.sub(r'\s+', ' ', name)
    if len(name) > _MAX_FILENAME_LEN:
        name = name[:_MAX_FILENAME_LEN].rstrip()
    return name


def _check_cancel(cancel_check: CancelCheck):
    if cancel_check and cancel_check():
        raise DownloadCancelled()


def _run_subprocess(cmd: list[str], cancel_check: CancelCheck):
    """Run a subprocess with cancellation support via Popen + polling.

    NOTE: mp4decrypt requires DRM keys on the command line (--key kid:key).
    The tool does not support key files or stdin for key input. Keys will be
    visible in the process list while the subprocess runs. This is a known
    limitation of the mp4decrypt CLI interface.
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=_NO_WINDOW,
    )
    try:
        while proc.poll() is None:
            if cancel_check and cancel_check():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                raise DownloadCancelled()
            try:
                proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
        if proc.returncode != 0:
            stderr = proc.stderr.read().decode(errors="replace").strip()
            stdout = proc.stdout.read().decode(errors="replace").strip()
            detail = stderr or stdout or "no output"
            cmd_name = os.path.basename(cmd[0])
            raise RuntimeError(
                f"{cmd_name} failed (exit {proc.returncode}): {detail}"
            )
    except DownloadCancelled:
        raise
    except RuntimeError:
        raise
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def download_encrypted(
    mpd_url: str,
    output_prefix: str,
    progress_cb: ProgressCb = None,
    cancel_check: CancelCheck = None,
) -> tuple[str, str]:
    """Download encrypted video and audio via yt-dlp library."""
    video_out = f"{output_prefix}_video_enc.mp4"
    audio_out = f"{output_prefix}_audio_enc.m4a"

    # Weight: video download 0-50%, audio download 50-75%
    phase_ranges = [
        ("downloading_video", "bestvideo", video_out, 0.0, 0.50),
        ("downloading_audio", "bestaudio", audio_out, 0.50, 0.75),
    ]

    for phase_key, fmt, out_path, range_start, range_end in phase_ranges:
        _check_cancel(cancel_check)

        def hook(d, _key=phase_key, _rs=range_start, _re=range_end):
            # Check cancel inside the download hook for responsive cancellation
            if cancel_check and cancel_check():
                raise yt_dlp.utils.DownloadCancelled("Cancelled by user")

            if d["status"] == "downloading" and progress_cb:
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                dl = d.get("downloaded_bytes", 0)
                raw_pct = (dl / total) if total > 0 else 0
                overall_pct = _rs + raw_pct * (_re - _rs)
                speed = d.get("speed") or 0
                eta_secs = 0
                if speed > 0 and total > 0:
                    eta_secs = int((total - dl) / speed)
                progress_cb(_key, overall_pct, {
                    "speed": speed,
                    "eta_secs": eta_secs,
                })

        opts = {
            "format": fmt,
            "allow_unplayable_formats": True,
            "outtmpl": out_path,
            "overwrites": True,
            "nopart": True,
            "fixup": "never",
            "postprocessors": [],
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([mpd_url])
        except yt_dlp.utils.DownloadCancelled:
            raise DownloadCancelled()

    return video_out, audio_out


def decrypt_file(
    input_path: str,
    output_path: str,
    keys: list[tuple[str, str]],
    cancel_check: CancelCheck = None,
):
    """Decrypt a file using mp4decrypt with cancellation support.

    NOTE: mp4decrypt only accepts keys via command-line arguments.
    There is no keyfile or stdin mode available. Keys are briefly
    visible in the process list while mp4decrypt runs.
    """
    mp4decrypt = get_binary("mp4decrypt")
    cmd = [mp4decrypt]
    for kid, key in keys:
        cmd.extend(["--key", f"{kid}:{key}"])
    cmd.extend([input_path, output_path])
    _run_subprocess(cmd, cancel_check)


def mux_output(
    video_path: str,
    audio_path: str,
    output_path: str,
    cancel_check: CancelCheck = None,
):
    """Mux decrypted video and audio into final MP4 with cancellation support."""
    ffmpeg = get_binary("ffmpeg")
    _run_subprocess(
        [ffmpeg, "-y", "-i", video_path, "-i", audio_path,
         "-c", "copy", "-movflags", "+faststart", output_path],
        cancel_check,
    )


def cleanup(*files):
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
        except OSError:
            pass


def download_episode(
    api,
    media_id: int,
    episode_id: int,
    output_dir: str,
    progress_cb: ProgressCb = None,
    cancel_check: CancelCheck = None,
) -> DownloadResult:
    """Full pipeline: fetch metadata, get keys, download, decrypt, mux.

    progress_cb receives (phase_key, pct, extra_dict) where phase_key
    is an i18n translation key.
    """

    # Track temp files for cleanup on any failure
    temp_files: list[str] = []

    try:
        if progress_cb:
            progress_cb("fetching_info", 0, {})

        _check_cancel(cancel_check)

        media = api.get_media_detail(media_id)
        episode = api.find_episode(media, episode_id)
        if not episode:
            return DownloadResult(False, error=f"Episode {episode_id} not found")

        media_title = media.get("mediaTitle", f"media_{media_id}")
        ep_name = episode.get("name", f"episode_{episode_id}")

        fname = safe_filename(media_title, ep_name)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_prefix = str(Path(output_dir) / fname)
        final_output = f"{output_prefix}.mp4"

        final_path = Path(final_output)
        if final_path.exists() and final_path.stat().st_size > 0:
            return DownloadResult(True, output_path=final_output)

        _check_cancel(cancel_check)

        if progress_cb:
            progress_cb("getting_drm", 0.02, {})

        drm_token = api.get_episode_drm_token(episode_id)
        mpd_url = (
            drm_token.get("androidPlaylistURL")
            or episode.get("fileUrl", "").replace("master.m3u8", "manifest.mpd")
        )
        if not mpd_url:
            return DownloadResult(False, error="No manifest URL found")

        if drm_token.get("isProtected"):
            if progress_cb:
                progress_cb("getting_keys", 0.03, {})
            keys = get_widevine_keys(mpd_url, drm_token)

            # download_encrypted uses weighted progress: video 0-50%, audio 50-75%
            video_enc, audio_enc = download_encrypted(
                mpd_url, output_prefix, progress_cb, cancel_check,
            )
            temp_files.extend([video_enc, audio_enc])

            _check_cancel(cancel_check)

            # Decrypt: 75-85%
            if progress_cb:
                progress_cb("decrypting_video", 0.75, {})
            video_dec = f"{output_prefix}_video_dec.mp4"
            audio_dec = f"{output_prefix}_audio_dec.m4a"
            temp_files.extend([video_dec, audio_dec])

            decrypt_file(video_enc, video_dec, keys, cancel_check)

            if progress_cb:
                progress_cb("decrypting_audio", 0.85, {})
            decrypt_file(audio_enc, audio_dec, keys, cancel_check)

            # Mux: 90-100%
            if progress_cb:
                progress_cb("muxing", 0.90, {})
            mux_output(video_dec, audio_dec, final_output, cancel_check)

            # Only clean temp files on success
            cleanup(*temp_files)
            temp_files.clear()
        else:
            # Not DRM protected — download with progress and cancellation
            def hls_hook(d):
                if cancel_check and cancel_check():
                    raise yt_dlp.utils.DownloadCancelled("Cancelled by user")
                if d["status"] == "downloading" and progress_cb:
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    dl = d.get("downloaded_bytes", 0)
                    raw_pct = (dl / total) if total > 0 else 0
                    speed = d.get("speed") or 0
                    eta_secs = 0
                    if speed > 0 and total > 0:
                        eta_secs = int((total - dl) / speed)
                    progress_cb("downloading_video", raw_pct, {
                        "speed": speed,
                        "eta_secs": eta_secs,
                    })

            hls_url = episode.get("fileUrl", mpd_url)
            opts = {
                "outtmpl": final_output,
                "quiet": True,
                "fixup": "never",
                "postprocessors": [],
                "progress_hooks": [hls_hook],
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([hls_url])
            except yt_dlp.utils.DownloadCancelled:
                raise DownloadCancelled()

        return DownloadResult(True, output_path=final_output)

    except DownloadCancelled:
        return DownloadResult(False, error="Cancelled", cancelled=True)
    except Exception as e:
        import logging
        logging.getLogger("seenshow.downloader").error(
            f"Download failed for episode {episode_id}: {e}", exc_info=True
        )
        return DownloadResult(False, error=str(e))
    finally:
        # Always clean temp files on failure/cancel (but not the final output)
        if temp_files:
            cleanup(*temp_files)
