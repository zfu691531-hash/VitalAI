#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目开发总入口。

用法：
1. `python main.py`
   启动后端 Uvicorn + 前端 Vite 开发服务
2. `python main.py --static-frontend`
   启动后端 Uvicorn + 前端 dist 静态服务

两个子进程都会托管在当前终端，按一次 Ctrl+C 即可一起停止。
"""

from __future__ import annotations

import argparse
import http.client
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"

DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_PORT = 5173


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一键启动 AIStu 前后端")
    parser.add_argument(
        "--static-frontend",
        action="store_true",
        help="前端不启 Vite，改为使用 frontend/dist 静态服务",
    )
    parser.add_argument("--backend-host", default=DEFAULT_BACKEND_HOST)
    parser.add_argument("--backend-port", type=int, default=DEFAULT_BACKEND_PORT)
    parser.add_argument("--frontend-host", default=DEFAULT_FRONTEND_HOST)
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT)
    return parser.parse_args()


def start_process(name: str, command: list[str], cwd: Path) -> subprocess.Popen:
    print(f"[start] {name}: {' '.join(command)}")
    popen_kwargs = {
        "cwd": str(cwd),
        "stdin": subprocess.DEVNULL,
        "stdout": None,
        "stderr": None,
        "bufsize": 1,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **popen_kwargs)


def stop_process(name: str, process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return

    print(f"[stop] {name}")
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def build_backend_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        args.backend_host,
        "--port",
        str(args.backend_port),
    ]


def build_frontend_command(args: argparse.Namespace) -> tuple[list[str], Path, str]:
    if args.static_frontend:
        if not FRONTEND_DIST_DIR.exists():
            raise FileNotFoundError(
                "未找到 frontend/dist。请先在 frontend 目录执行 npm run build，再使用 --static-frontend。"
            )
        return (
            [
                sys.executable,
                "-m",
                "http.server",
                str(args.frontend_port),
                "-b",
                args.frontend_host,
            ],
            FRONTEND_DIST_DIR,
            "frontend-static",
        )

    return (
        ["npm.cmd", "run", "dev", "--", "--host", args.frontend_host, "--port", str(args.frontend_port)],
        FRONTEND_DIR,
        "frontend-dev",
    )


def wait_for_http(host: str, port: int, path: str = "/", timeout_seconds: int = 20) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            connection = http.client.HTTPConnection(host, port, timeout=2)
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            connection.close()
            return True
        except Exception:
            time.sleep(1)
    return False


def main() -> int:
    args = parse_args()
    backend_process: subprocess.Popen | None = None
    frontend_process: subprocess.Popen | None = None

    try:
        backend_process = start_process(
            "backend",
            build_backend_command(args),
            BACKEND_DIR,
        )
        time.sleep(2)

        if backend_process.poll() is not None:
            print("[error] 后端启动失败，已停止总启动流程。")
            return backend_process.returncode or 1
        if not wait_for_http(args.backend_host, args.backend_port, "/health", timeout_seconds=20):
            print("[error] 后端进程已启动，但健康检查未通过。")
            return 1

        frontend_command, frontend_cwd, frontend_name = build_frontend_command(args)
        frontend_process = start_process(frontend_name, frontend_command, frontend_cwd)
        time.sleep(2)

        if frontend_process.poll() is not None:
            print("[error] 前端启动失败，准备关闭后端。")
            return frontend_process.returncode or 1
        if not wait_for_http(args.frontend_host, args.frontend_port, "/", timeout_seconds=20):
            print("[error] 前端进程已启动，但页面探活未通过。")
            return 1

        print("[ready] 前后端已启动")
        print(f"[url] frontend: http://{args.frontend_host}:{args.frontend_port}")
        print(f"[url] backend docs: http://{args.backend_host}:{args.backend_port}/docs")
        print("[hint] 按 Ctrl+C 可一起停止前后端")

        while True:
            if backend_process.poll() is not None:
                print("[exit] 后端已退出，准备关闭前端。")
                return backend_process.returncode or 1
            if frontend_process.poll() is not None:
                print("[exit] 前端已退出，准备关闭后端。")
                return frontend_process.returncode or 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[signal] 收到 Ctrl+C，正在停止前后端...")
        return 0
    finally:
        stop_process("frontend", frontend_process)
        stop_process("backend", backend_process)


if __name__ == "__main__":
    if sys.platform == "win32":
        signal.signal(signal.SIGINT, signal.default_int_handler)
    raise SystemExit(main())
