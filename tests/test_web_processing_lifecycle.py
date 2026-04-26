from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from app.services import web_processing


class WebProcessingLifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.originals = {
            "processing_dir": web_processing.PROCESSING_DIR,
            "status_file": web_processing.STATUS_FILE,
            "preview_status_file": web_processing.PREVIEW_STATUS_FILE,
            "log_file": web_processing.LOG_FILE,
            "preview_log_file": web_processing.PREVIEW_LOG_FILE,
            "process": web_processing._PROCESS,  # noqa: SLF001
            "helper_process": web_processing._HELPER_PROCESS,  # noqa: SLF001
            "process_log_handle": web_processing._PROCESS_LOG_HANDLE,  # noqa: SLF001
        }
        web_processing.PROCESSING_DIR = self.temp_path
        web_processing.STATUS_FILE = self.temp_path / "status.json"
        web_processing.PREVIEW_STATUS_FILE = self.temp_path / "preview_status.json"
        web_processing.LOG_FILE = self.temp_path / "runner.log"
        web_processing.PREVIEW_LOG_FILE = self.temp_path / "preview_runner.log"
        web_processing._PROCESS = None  # noqa: SLF001
        web_processing._HELPER_PROCESS = None  # noqa: SLF001
        web_processing._PROCESS_LOG_HANDLE = None  # noqa: SLF001

    def tearDown(self) -> None:
        web_processing.PROCESSING_DIR = self.originals["processing_dir"]
        web_processing.STATUS_FILE = self.originals["status_file"]
        web_processing.PREVIEW_STATUS_FILE = self.originals["preview_status_file"]
        web_processing.LOG_FILE = self.originals["log_file"]
        web_processing.PREVIEW_LOG_FILE = self.originals["preview_log_file"]
        web_processing._PROCESS = self.originals["process"]  # noqa: SLF001
        web_processing._HELPER_PROCESS = self.originals["helper_process"]  # noqa: SLF001
        web_processing._PROCESS_LOG_HANDLE = self.originals["process_log_handle"]  # noqa: SLF001
        self.temp_dir.cleanup()

    def write_status(self, payload: dict) -> None:
        web_processing.STATUS_FILE.write_text(json.dumps(payload), encoding="utf-8")

    def test_current_status_fails_stale_runner_boot_and_releases_process(self) -> None:
        started_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds=web_processing.RUNNER_BOOT_TIMEOUT_SECONDS + 30)
        ).isoformat()
        self.write_status(
            {
                "status": "starting",
                "message": "Browser-Direktlauf wurde gestartet.",
                "startedAt": started_at,
                "pid": 12345,
            }
        )

        with mock.patch.object(
            web_processing,
            "_terminate_process",
            return_value=True,
        ) as terminate_process:
            status = web_processing.current_status()

        terminate_process.assert_called_once()
        self.assertEqual("failed", status["status"])
        self.assertTrue(status["staleRunnerKilled"])
        self.assertIn("Headless-Runner", status["message"])

    def test_stop_job_uses_process_tree_termination_for_orphan_pid(self) -> None:
        self.write_status(
            {
                "status": "running",
                "message": "Laeuft",
                "startedAt": datetime.now(timezone.utc).isoformat(),
                "pid": 23456,
            }
        )

        with mock.patch.object(
            web_processing,
            "_is_pid_running",
            side_effect=[True, False],
        ), mock.patch.object(
            web_processing,
            "_terminate_process",
            return_value=True,
        ) as terminate_process:
            status = web_processing.stop_job()

        terminate_process.assert_called_once_with(None, 23456)
        self.assertEqual("stopped", status["status"])
        self.assertFalse(status["active"])

    def test_current_status_reports_active_helper_with_preview_log(self) -> None:
        class RunningHelper:
            pid = 34567

            def poll(self):
                return None

        web_processing._HELPER_PROCESS = RunningHelper()  # noqa: SLF001
        web_processing.PREVIEW_STATUS_FILE.write_text(
            json.dumps(
                {
                    "status": "running",
                    "mode": "preview",
                    "message": "Geswappte Vorschau wird erzeugt.",
                    "pid": 34567,
                }
            ),
            encoding="utf-8",
        )
        web_processing.PREVIEW_LOG_FILE.write_text(
            "preview log line\n",
            encoding="utf-8",
        )

        with mock.patch.object(web_processing, "_is_pid_running", return_value=True):
            status = web_processing.current_status()

        self.assertEqual("running", status["status"])
        self.assertTrue(status["active"])
        self.assertEqual(str(web_processing.PREVIEW_LOG_FILE), status["logPath"])
        self.assertEqual(["preview log line"], status["logTail"])


if __name__ == "__main__":
    unittest.main()
