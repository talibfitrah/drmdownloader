"""Threaded batch download manager with progress and cancellation."""

import queue
import threading
from dataclasses import dataclass


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

    def _run(self, tasks: list[EpisodeTask]):
        from ..core.downloader import download_episode

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

            result = download_episode(
                api=self.api,
                media_id=task.media_id,
                episode_id=task.episode_id,
                output_dir=self.output_dir,
                progress_cb=progress_cb,
                cancel_check=self._cancel.is_set,
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
                self.status_queue.put(StatusUpdate(
                    task.episode_id, "error", 0,
                    result.error, result.error,
                ))

        # Determine batch terminal state
        if any_cancelled:
            terminal = "batch_cancelled"
        elif any_error:
            terminal = "batch_error"
        else:
            terminal = "batch_done"

        self.status_queue.put(StatusUpdate(0, terminal, 1.0, terminal))
