"""One-command dev helper: start VitalAI backend, wait for health, optionally smoke, then stop.

Usage examples:
    python scripts/dev_start_and_smoke.py                   # start, wait for health, stop
    python scripts/dev_start_and_smoke.py --smoke           # start, smoke, stop
    python scripts/dev_start_and_smoke.py --smoke --keep-running   # start, smoke, keep alive
    python scripts/dev_start_and_smoke.py --keep-running     # start, keep alive for manual testing
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8124
DEFAULT_STARTUP_TIMEOUT = 30.0
HEALTH_PATH = "/vitalai/health"
POLL_INTERVAL = 0.5


def _build_base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _check_health(base_url: str, timeout_seconds: float = 5.0) -> bool:
    """Return True if the health endpoint responds with status=ok."""
    url = f"{base_url.rstrip('/')}{HEALTH_PATH}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("status") == "ok"
    except Exception:
        return False


def _wait_for_health(
    base_url: str,
    timeout: float,
    *,
    proc: subprocess.Popen | None = None,
) -> None:
    """Poll the health endpoint until it responds or timeout is reached.

    Raises RuntimeError on timeout or when the server process exits early.
    """
    deadline = time.monotonic() + timeout
    attempt = 0
    while time.monotonic() < deadline:
        if proc is not None:
            exit_code = proc.poll()
            if exit_code is not None:
                raise RuntimeError(
                    f"VitalAI server exited before health check passed (exit_code={exit_code})."
                )
        attempt += 1
        if _check_health(base_url):
            return
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(POLL_INTERVAL, remaining))
    raise RuntimeError(
        f"VitalAI health check timed out after {timeout:.1f}s "
        f"({attempt} attempts). Is the server running at {base_url}?"
    )


def _start_server(host: str, port: int) -> subprocess.Popen:
    """Start uvicorn as a subprocess and return the Popen object."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "VitalAI.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    env = os.environ.copy()
    return subprocess.Popen(cmd, cwd=str(ROOT_DIR), env=env)


def _run_smoke(base_url: str, smoke_output: str) -> int:
    """Run the existing manual_smoke_http_api.py and return its exit code."""
    smoke_script = ROOT_DIR / "scripts" / "manual_smoke_http_api.py"
    cmd = [
        sys.executable,
        str(smoke_script),
        "--base-url",
        base_url,
        "--output",
        smoke_output,
    ]
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    return result.returncode


def _terminate_server(proc: subprocess.Popen) -> None:
    """Best-effort terminate the server subprocess."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
    except OSError:
        pass


def run(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    smoke: bool = False,
    keep_running: bool = False,
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
    smoke_output: str = "text",
) -> int:
    """Main entry point. Returns exit code (0=success, non-zero=failure)."""
    base_url = _build_base_url(host, port)
    proc: subprocess.Popen | None = None

    def _cleanup() -> None:
        if proc is not None:
            _terminate_server(proc)

    try:
        print(f"[dev_start_and_smoke] Starting VitalAI at {base_url} ...")
        proc = _start_server(host, port)

        print(f"[dev_start_and_smoke] Waiting for health check (timeout={startup_timeout:.0f}s) ...")
        _wait_for_health(base_url, startup_timeout, proc=proc)
        print(f"[dev_start_and_smoke] Health check passed.")

        if smoke:
            print(f"[dev_start_and_smoke] Running HTTP smoke (output={smoke_output}) ...")
            smoke_rc = _run_smoke(base_url, smoke_output)
            if smoke_rc != 0:
                print("[dev_start_and_smoke] Smoke FAILED.", file=sys.stderr)
                return 1
            print("[dev_start_and_smoke] Smoke passed.")

        if keep_running:
            print(f"[dev_start_and_smoke] Server running at {base_url}")
            print("[dev_start_and_smoke] Press Ctrl+C to stop.")
            while proc.poll() is None:
                time.sleep(0.5)
            print("[dev_start_and_smoke] Server process exited.")
            return proc.returncode or 0

        return 0

    except KeyboardInterrupt:
        print("\n[dev_start_and_smoke] Interrupted by user.")
        return 130
    except RuntimeError as exc:
        print(f"[dev_start_and_smoke] ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        _cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start VitalAI backend, optionally run smoke, then stop.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Listen host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Listen port (default: {DEFAULT_PORT})")
    parser.add_argument(
        "--smoke", action="store_true", help="Run HTTP smoke after server is healthy."
    )
    parser.add_argument(
        "--keep-running", action="store_true", help="Keep server running after smoke (or immediately if no smoke)."
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=DEFAULT_STARTUP_TIMEOUT,
        help=f"Max seconds to wait for health check (default: {DEFAULT_STARTUP_TIMEOUT}).",
    )
    parser.add_argument(
        "--smoke-output",
        choices=("text", "json"),
        default="text",
        help="Smoke report format (default: text).",
    )
    args = parser.parse_args()

    return run(
        host=args.host,
        port=args.port,
        smoke=args.smoke,
        keep_running=args.keep_running,
        startup_timeout=args.startup_timeout,
        smoke_output=args.smoke_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
