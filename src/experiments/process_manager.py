"""Starts/stops/kills the application processes as real OS processes.

Using real subprocesses (rather than in-process FastAPI test clients) is
what makes "crash" a genuine fault: SIGKILL actually terminates the worker,
and "restart" actually launches a new process.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import httpx

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ManagedProcess:
    def __init__(self, name: str, module: str, port: int, extra_env: dict | None = None):
        self.name = name
        self.module = module
        self.port = port
        self.extra_env = extra_env or {}
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        env = os.environ.copy()
        env.update(self.extra_env)
        self.proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", self.module,
                "--host", "127.0.0.1", "--port", str(self.port),
                "--log-level", "warning",
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def pid(self) -> int | None:
        return self.proc.pid if self.proc else None

    def kill(self) -> None:
        """Simulates a hard crash: SIGKILL, no graceful shutdown."""
        if self.proc and self.is_alive():
            self.proc.kill()
            self.proc.wait(timeout=5)

    def stop_gracefully(self) -> None:
        if self.proc and self.is_alive():
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def wait_until_healthy(self, timeout_seconds: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout_seconds
        url = f"http://127.0.0.1:{self.port}/health"
        while time.monotonic() < deadline:
            try:
                r = httpx.get(url, timeout=1.0)
                if r.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        return False
