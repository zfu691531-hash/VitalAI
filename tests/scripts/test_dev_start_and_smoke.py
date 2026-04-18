"""Tests for scripts/dev_start_and_smoke.py."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from scripts.dev_start_and_smoke import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_STARTUP_TIMEOUT,
    _build_base_url,
    _check_health,
    _terminate_server,
    _wait_for_health,
    main,
    run,
)


class BuildBaseUrlTests(unittest.TestCase):
    def test_default_values(self) -> None:
        self.assertEqual("http://127.0.0.1:8124", _build_base_url(DEFAULT_HOST, DEFAULT_PORT))

    def test_custom_values(self) -> None:
        self.assertEqual("http://0.0.0.0:9000", _build_base_url("0.0.0.0", 9000))


class CheckHealthTests(unittest.TestCase):
    @patch("scripts.dev_start_and_smoke.urlopen")
    def test_returns_true_when_status_ok(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok", "module": "VitalAI"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.assertTrue(_check_health("http://127.0.0.1:8124"))

    @patch("scripts.dev_start_and_smoke.urlopen")
    def test_returns_false_when_status_not_ok(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "degraded"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        self.assertFalse(_check_health("http://127.0.0.1:8124"))

    @patch("scripts.dev_start_and_smoke.urlopen")
    def test_returns_false_on_network_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = Exception("connection refused")

        self.assertFalse(_check_health("http://127.0.0.1:8124"))


class WaitForHealthTests(unittest.TestCase):
    @patch("scripts.dev_start_and_smoke._check_health", return_value=True)
    def test_returns_immediately_on_success(self, mock_check: MagicMock) -> None:
        _wait_for_health("http://127.0.0.1:8124", timeout=5.0)

        mock_check.assert_called_once()

    @patch("scripts.dev_start_and_smoke.time.sleep")
    @patch("scripts.dev_start_and_smoke.time.monotonic", side_effect=[0, 0, 0, 2, 2])
    @patch("scripts.dev_start_and_smoke._check_health", return_value=False)
    def test_raises_on_timeout(
        self,
        mock_check: MagicMock,
        mock_time: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _wait_for_health("http://127.0.0.1:8124", timeout=1.0)

        self.assertIn("timed out", str(ctx.exception))
        self.assertTrue(mock_check.called)

    @patch("scripts.dev_start_and_smoke.time.sleep")
    @patch("scripts.dev_start_and_smoke.time.monotonic", side_effect=[0, 0.1])
    def test_raises_when_server_process_exits_early(
        self,
        mock_time: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 3

        with self.assertRaises(RuntimeError) as ctx:
            _wait_for_health("http://127.0.0.1:8124", timeout=5.0, proc=mock_proc)

        self.assertIn("exited before health check passed", str(ctx.exception))


class TerminateServerTests(unittest.TestCase):
    def test_terminate_live_process(self) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = 0

        _terminate_server(mock_proc)

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_not_called()

    def test_skip_already_exited(self) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1

        _terminate_server(mock_proc)

        mock_proc.terminate.assert_not_called()

    def test_kill_on_terminate_timeout(self) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5), None]

        _terminate_server(mock_proc)

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()


class RunIntegrationTests(unittest.TestCase):
    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._run_smoke", return_value=0)
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_smoke_success_path(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_smoke: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_start.return_value = mock_proc

        rc = run(smoke=True, keep_running=False)

        self.assertEqual(0, rc)
        mock_start.assert_called_once_with(DEFAULT_HOST, DEFAULT_PORT)
        mock_wait.assert_called_once_with(
            f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
            DEFAULT_STARTUP_TIMEOUT,
            proc=mock_proc,
        )
        mock_smoke.assert_called_once_with(f"http://{DEFAULT_HOST}:{DEFAULT_PORT}", "text")
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._run_smoke", return_value=1)
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_smoke_failure_returns_nonzero(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_smoke: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc

        rc = run(smoke=True)

        self.assertEqual(1, rc)
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._wait_for_health", side_effect=RuntimeError("timed out"))
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_startup_timeout_returns_nonzero(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc

        rc = run()

        self.assertEqual(1, rc)
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_no_smoke_no_keep_just_starts_and_stops(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc

        rc = run(smoke=False, keep_running=False)

        self.assertEqual(0, rc)
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke.time.sleep")
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_keep_running_waits_for_process_exit(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_sleep: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc
        mock_proc.poll.side_effect = [None, None, 0]
        mock_proc.returncode = 0

        rc = run(smoke=False, keep_running=True)

        self.assertEqual(0, rc)
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_keyboard_interrupt_returns_130(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc
        mock_wait.side_effect = KeyboardInterrupt()

        rc = run()

        self.assertEqual(130, rc)
        mock_term.assert_called_once_with(mock_proc)

    @patch("scripts.dev_start_and_smoke._terminate_server")
    @patch("scripts.dev_start_and_smoke._run_smoke", return_value=0)
    @patch("scripts.dev_start_and_smoke._wait_for_health")
    @patch("scripts.dev_start_and_smoke._start_server")
    def test_custom_host_port_passed_correctly(
        self,
        mock_start: MagicMock,
        mock_wait: MagicMock,
        mock_smoke: MagicMock,
        mock_term: MagicMock,
    ) -> None:
        mock_proc = MagicMock()
        mock_start.return_value = mock_proc

        rc = run(host="0.0.0.0", port=9999, smoke=True, smoke_output="json")

        self.assertEqual(0, rc)
        mock_start.assert_called_once_with("0.0.0.0", 9999)
        mock_wait.assert_called_once_with("http://0.0.0.0:9999", DEFAULT_STARTUP_TIMEOUT, proc=mock_proc)
        mock_smoke.assert_called_once_with("http://0.0.0.0:9999", "json")


class MainArgumentParsingTests(unittest.TestCase):
    @patch("scripts.dev_start_and_smoke.run", return_value=0)
    def test_main_uses_default_arguments(self, mock_run: MagicMock) -> None:
        with patch("scripts.dev_start_and_smoke.sys.argv", ["dev_start_and_smoke.py"]):
            exit_code = main()

        self.assertEqual(0, exit_code)
        mock_run.assert_called_once_with(
            host=DEFAULT_HOST,
            port=DEFAULT_PORT,
            smoke=False,
            keep_running=False,
            startup_timeout=DEFAULT_STARTUP_TIMEOUT,
            smoke_output="text",
        )

    @patch("scripts.dev_start_and_smoke.run", return_value=0)
    def test_main_passes_custom_arguments(self, mock_run: MagicMock) -> None:
        with patch(
            "scripts.dev_start_and_smoke.sys.argv",
            [
                "dev_start_and_smoke.py",
                "--host",
                "0.0.0.0",
                "--port",
                "9001",
                "--smoke",
                "--keep-running",
                "--startup-timeout",
                "12.5",
                "--smoke-output",
                "json",
            ],
        ):
            exit_code = main()

        self.assertEqual(0, exit_code)
        mock_run.assert_called_once_with(
            host="0.0.0.0",
            port=9001,
            smoke=True,
            keep_running=True,
            startup_timeout=12.5,
            smoke_output="json",
        )


if __name__ == "__main__":
    unittest.main()
