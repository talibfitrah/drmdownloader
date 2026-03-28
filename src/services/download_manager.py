"""Threaded batch download manager with progress, retry, and cancellation."""

import logging
import queue
import shutil
import threading
import time
import traceback
from dataclasses import dataclass

from ..core.downloader import download_episode, cleanup, safe_filename, DownloadResult

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds; exponential: 2, 4, 8
MIN_DISK_SPACE_MB = 500  # Minimum free disk space in MB


@dataclass
class EpisodeTask:
    media_id: int
    episode_id: int
    name: str
    duration: str = ""


@dataclass
class StatusUpdate:
    episode_id: int
    phase: str        # "downloading","decrypting","muxing","done","error","cancelled"
    progress: float   # 0.0 - 1.0
    message: str      # pre-translated display string
    error: str = ""


def _is_retryable(error_str: str) -> bool:
    """Check if an error is transient and worth retrying."""
    retryable_patterns = [
        "timeout", "timed out", "connection", "temporary",
        "503", "502", "500", "429", "network",
    ]
    lower = error_str.lower()
    return any(p in lower for p in retryable_patterns)


class DownloadManager:
    """Runs episode downloads sequentially in a background thread."""

    def __init__(self, api, output_dir: str, i18n=None):
        self.api = api
        self.output_dir = output_dir
        self.i18n = i18n
        self.status_queue: queue.Queue[StatusUpdate] = queue.Queue()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def cancel(self):
        self._cancel.set()

    def join(self, timeout: float | None = None):
        """Wait for the background thread to finish."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def start(self, tasks: list[EpisodeTask]):
        if self.is_running:
            return
        self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(tasks,), daemon=True
        )
        self._thread.start()

    def _translate(self, key: str, extra: dict | None = None) -> str:
        """Translate a phase key into a display string."""
        extra = extra or {}
        i = self.i18n

        if not i:
            return key

        base = i.t(key)

        # Format speed/ETA for download phases
        speed = extra.get("speed", 0)
        eta_secs = extra.get("eta_secs", 0)

        parts = [base]
        if speed > 0:
            if speed >= 1_048_576:
                parts.append(f"({speed / 1_048_576:.1f} MB/s)")
            elif speed >= 1024:
                parts.append(f"({speed / 1024:.0f} KB/s)")

        if eta_secs > 0:
            if eta_secs >= 3600:
                parts.append(f"— {i.t('eta_h', eta_secs // 3600, (eta_secs % 3600) // 60)}")
            elif eta_secs >= 60:
                parts.append(f"— {i.t('eta_m', eta_secs // 60, eta_secs % 60)}")
            else:
                parts.append(f"— {i.t('eta_s', eta_secs)}")

        return " ".join(parts)

    def _check_disk_space(self) -> bool:
        """Check if there's enough free disk space in the output directory."""
        try:
            usage = shutil.disk_usage(self.output_dir)
            free_mb = usage.free / (1024 * 1024)
            return free_mb >= MIN_DISK_SPACE_MB
        except OSError:
            # Can't check — proceed anyway
            return True

    def _run(self, tasks: list[EpisodeTask]):
        try:
            self._run_tasks(tasks)
        except Exception:
            logger.error("Download manager crashed: %s", traceback.format_exc())
            self.status_queue.put(StatusUpdate(
                0, "batch_error", 0,
                self._translate("error"),
                error=traceback.format_exc(),
            ))

    def _run_tasks(self, tasks: list[EpisodeTask]):

        any_cancelled = False
        any_error = False

        for i_task, task in enumerate(tasks):
            if self._cancel.is_set():
                any_cancelled = True
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "cancelled", 0,
                    self._translate("cancelled"),
                ))
                continue

            # Check disk space before starting each task
            if not self._check_disk_space():
                any_error = True
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "error", 0,
                    self._translate("disk_space_error"),
                    error="Insufficient disk space",
                ))
                continue

            def progress_cb(phase_key, pct, extra, _eid=task.episode_id):
                phase = "downloading"
                if "decrypt" in phase_key:
                    phase = "decrypting"
                elif "mux" in phase_key:
                    phase = "muxing"
                msg = self._translate(phase_key, extra)
                self.status_queue.put(StatusUpdate(
                    _eid, phase, pct, msg,
                ))

            start_msg = self.i18n.t("starting", i_task + 1, len(tasks)) if self.i18n else f"Starting ({i_task+1}/{len(tasks)})..."
            self.status_queue.put(StatusUpdate(
                task.episode_id, "downloading", 0, start_msg,
            ))

            result = self._download_with_retry(
                task, i_task, len(tasks), download_episode, progress_cb,
            )

            if result.cancelled:
                any_cancelled = True
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "cancelled", 0,
                    self._translate("cancelled"),
                ))
            elif result.success:
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "done", 1.0,
                    self._translate("done"),
                ))
            else:
                any_error = True
                # Clean up partial download files on final failure
                try:
                    self._cleanup_partial_files(task)
                except Exception as e:
                    logger.warning("Cleanup failed for episode %s: %s", task.episode_id, e)
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "error", 0,
                    self._translate("download_error"),
                    error=result.error,
                ))

        # Determine batch terminal state
        if any_cancelled:
            terminal = "batch_cancelled"
        elif any_error:
            terminal = "batch_error"
        else:
            terminal = "batch_done"

        self.status_queue.put(StatusUpdate(0, terminal, 1.0, terminal))

    def _download_with_retry(self, task, i_task, total, download_fn, progress_cb):
        """Attempt download with exponential backoff for transient failures."""

        last_result = None
        for attempt in range(MAX_RETRIES + 1):
            if self._cancel.is_set():
                return DownloadResult(False, error="Cancelled", cancelled=True)

            result = download_fn(
                api=self.api,
                media_id=task.media_id,
                episode_id=task.episode_id,
                output_dir=self.output_dir,
                progress_cb=progress_cb,
                cancel_check=self._cancel.is_set,
            )
            last_result = result

            if result.success or result.cancelled:
                return result

            # Check if error is retryable
            if attempt < MAX_RETRIES and _is_retryable(result.error):
                wait = BACKOFF_BASE ** (attempt + 1)
                retry_msg = (
                    self.i18n.t("retrying", attempt + 2, MAX_RETRIES + 1)
                    if self.i18n
                    else f"Retrying ({attempt + 2}/{MAX_RETRIES + 1})..."
                )
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "downloading", 0, retry_msg,
                ))
                # Wait with cancel check
                deadline = time.time() + wait
                while time.time() < deadline:
                    if self._cancel.is_set():
                        return DownloadResult(False, error="Cancelled", cancelled=True)
                    time.sleep(0.5)
            else:
                break

        return last_result

    def _cleanup_partial_files(self, task):
        """Remove partial/temp files for a failed task."""
        from pathlib import Path

        try:
            media_detail = self.api.get_media_detail(task.media_id)
            media_title = media_detail.get("mediaTitle", f"media_{task.media_id}")
        except Exception:
            media_title = f"media_{task.media_id}"

        fname = safe_filename(media_title, task.name)
        prefix = str(Path(self.output_dir) / fname)

        partial_patterns = [
            f"{prefix}_video_enc.mp4",
            f"{prefix}_audio_enc.m4a",
            f"{prefix}_video_dec.mp4",
            f"{prefix}_audio_dec.m4a",
        ]
        cleanup(*partial_patterns)
