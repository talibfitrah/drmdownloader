"""Tests for download manager — terminal states, cancellation."""

import queue
import time
from unittest.mock import patch, MagicMock

from src.services.download_manager import DownloadManager, EpisodeTask, StatusUpdate
from src.core.downloader import DownloadResult


def _make_task(eid=1):
    return EpisodeTask(media_id=100, episode_id=eid, name=f"ep{eid}", duration="10:00")


class TestDownloadManager:
    def _drain(self, dm, timeout=5) -> list[StatusUpdate]:
        """Collect all status updates until a terminal state."""
        updates = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                u = dm.status_queue.get(timeout=0.1)
                updates.append(u)
                if u.phase.startswith("batch_"):
                    return updates
            except queue.Empty:
                pass
        return updates

    def test_successful_batch_emits_batch_done(self):
        mock_api = MagicMock()
        dm = DownloadManager(api=mock_api, output_dir="/tmp")

        mock_result = DownloadResult(success=True, output_path="/tmp/out.mp4")
        with patch("src.core.downloader.download_episode", return_value=mock_result):
            dm.start([_make_task(1)])
            updates = self._drain(dm)

        terminals = [u for u in updates if u.phase.startswith("batch_")]
        assert len(terminals) == 1
        assert terminals[0].phase == "batch_done"

    def test_failed_download_emits_batch_error(self):
        mock_api = MagicMock()
        dm = DownloadManager(api=mock_api, output_dir="/tmp")

        mock_result = DownloadResult(success=False, error="DRM failed")
        with patch("src.core.downloader.download_episode", return_value=mock_result):
            dm.start([_make_task(1)])
            updates = self._drain(dm)

        error_updates = [u for u in updates if u.phase == "error"]
        assert len(error_updates) == 1
        terminals = [u for u in updates if u.phase.startswith("batch_")]
        assert terminals[0].phase == "batch_error"

    def test_cancelled_download_emits_batch_cancelled(self):
        mock_api = MagicMock()
        dm = DownloadManager(api=mock_api, output_dir="/tmp")

        mock_result = DownloadResult(success=False, error="Cancelled", cancelled=True)
        with patch("src.core.downloader.download_episode", return_value=mock_result):
            dm.start([_make_task(1)])
            updates = self._drain(dm)

        cancelled_updates = [u for u in updates if u.phase == "cancelled"]
        assert len(cancelled_updates) >= 1
        terminals = [u for u in updates if u.phase.startswith("batch_")]
        assert terminals[0].phase == "batch_cancelled"

    def test_cancel_during_first_episode_skips_rest(self):
        mock_api = MagicMock()
        dm = DownloadManager(api=mock_api, output_dir="/tmp")

        def mock_download(**kwargs):
            # First call succeeds, then cancel kicks in for the rest
            dm.cancel()
            return DownloadResult(success=True, output_path="/tmp/1.mp4")

        with patch("src.core.downloader.download_episode", side_effect=mock_download):
            dm.start([_make_task(1), _make_task(2)])
            updates = self._drain(dm)

        # First episode done, second cancelled
        done = [u for u in updates if u.phase == "done"]
        cancelled = [u for u in updates if u.phase == "cancelled"]
        assert len(done) == 1
        assert len(cancelled) == 1
        terminals = [u for u in updates if u.phase.startswith("batch_")]
        assert terminals[0].phase == "batch_cancelled"

    def test_multi_episode_mixed_results(self):
        mock_api = MagicMock()
        dm = DownloadManager(api=mock_api, output_dir="/tmp")

        results = [
            DownloadResult(success=True, output_path="/tmp/1.mp4"),
            DownloadResult(success=False, error="Failed"),
        ]
        call_count = [0]

        def mock_download(**kwargs):
            r = results[call_count[0]]
            call_count[0] += 1
            return r

        with patch("src.core.downloader.download_episode", side_effect=mock_download):
            dm.start([_make_task(1), _make_task(2)])
            updates = self._drain(dm)

        done = [u for u in updates if u.phase == "done"]
        errors = [u for u in updates if u.phase == "error"]
        assert len(done) == 1
        assert len(errors) == 1
        terminals = [u for u in updates if u.phase.startswith("batch_")]
        assert terminals[0].phase == "batch_error"
