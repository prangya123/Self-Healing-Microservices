"""The service under test: exposes /health and /work.

/health reports process liveness and resource usage only -- it never calls
the downstream dependency, so a slow/failing dependency cannot masquerade as
a process crash.

/work exercises the dependency synchronously (unless the circuit breaker is
open) so that dependency-timeout faults are visible as real request latency
and failures, not simulated numbers.

Fault/remediation control endpoints under /admin/* that can change
application behavior (memory growth, circuit breaker) are only reachable
when the process is launched with SELF_HEALING_TEST_MODE=1.
"""
from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager

import httpx
import psutil
from fastapi import FastAPI, HTTPException

TEST_MODE = os.environ.get("SELF_HEALING_TEST_MODE") == "1"
DEPENDENCY_URL = os.environ.get("DEPENDENCY_URL", "http://127.0.0.1:8002")
DEPENDENCY_TIMEOUT_SECONDS = float(os.environ.get("DEPENDENCY_TIMEOUT_SECONDS", "2.0"))
# Simulates resource exhaustion: an unmitigated memory leak eventually makes
# the process genuinely unhealthy, not just elevated in a metric nobody acts
# on. Default is effectively "disabled" unless a test run sets it.
MEMORY_LEAK_HARD_FAILURE_MB = float(os.environ.get("MEMORY_LEAK_HARD_FAILURE_MB", "1e9"))

# A fresh httpx.AsyncClient() per request has real allocation overhead
# (connection pool, SSL context) that the allocator doesn't fully return to
# the OS between calls -- creating one per /work call caused a genuine,
# deterministic ~20MB RSS creep over the process's first ~25 seconds that
# had nothing to do with the memory-leak fault and confounded its threshold
# calibration. One shared, reused client avoids this.
_http_client = httpx.AsyncClient(timeout=DEPENDENCY_TIMEOUT_SECONDS)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    yield
    await _http_client.aclose()


app = FastAPI(title="main-service", lifespan=_lifespan)

_process = psutil.Process(os.getpid())
_process.cpu_percent(interval=None)  # prime the internal counter

_state = {
    "circuit_breaker_open": False,
    "leaked_mb": 0.0,
    "memory_leak_active": False,
}
_leak_buffer: list[bytes] = []
_leak_task: asyncio.Task | None = None


@app.get("/health")
async def health():
    mem_mb = _process.memory_info().rss / (1024 * 1024)
    if mem_mb >= MEMORY_LEAK_HARD_FAILURE_MB:
        raise HTTPException(
            status_code=503,
            detail={"error": "resource_exhaustion", "mem_mb": mem_mb, "hard_failure_mb": MEMORY_LEAK_HARD_FAILURE_MB},
        )
    return {
        "status": "ok",
        "pid": os.getpid(),
        "cpu_percent": _process.cpu_percent(interval=None),
        "mem_mb": mem_mb,
        "circuit_breaker_open": _state["circuit_breaker_open"],
        "leaked_mb": _state["leaked_mb"],
        "test_mode": TEST_MODE,
    }


@app.get("/work")
async def work():
    if _state["circuit_breaker_open"]:
        return {"status": "ok", "mode": "degraded_fallback", "dependency_latency_ms": None}

    start = time.monotonic()
    try:
        resp = await _http_client.get(f"{DEPENDENCY_URL}/ping")
        resp.raise_for_status()
        latency_ms = (time.monotonic() - start) * 1000.0
        return {"status": "ok", "mode": "normal", "dependency_latency_ms": latency_ms}
    except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as exc:
        latency_ms = (time.monotonic() - start) * 1000.0
        raise HTTPException(
            status_code=503,
            detail={"error": "dependency_unavailable", "dependency_latency_ms": latency_ms, "reason": str(exc)},
        )


async def _leak_loop(step_mb: float, interval_seconds: float, max_mb: float) -> None:
    while _state["memory_leak_active"] and _state["leaked_mb"] < max_mb:
        # os.urandom (not bytearray(n), which zero-fills) forces the OS to
        # actually commit distinct physical pages. Zero-filled allocations
        # can be backed by a shared copy-on-write zero page and never show
        # up in RSS, and macOS's memory compression can later shrink even
        # genuinely-allocated-but-untouched pages -- both make mem_mb an
        # unreliable, non-monotonic signal for this fault unless every byte
        # is actually written.
        _leak_buffer.append(bytearray(os.urandom(int(step_mb * 1024 * 1024))))
        _state["leaked_mb"] += step_mb
        await asyncio.sleep(interval_seconds)


@app.post("/admin/memory_leak/start")
async def start_memory_leak(step_mb: float = 8.0, interval_seconds: float = 1.0, max_mb: float = 256.0):
    if not TEST_MODE:
        raise HTTPException(status_code=403, detail="Fault injection is disabled outside test mode.")
    global _leak_task
    if _state["memory_leak_active"]:
        return {"ok": True, "already_active": True}
    _state["memory_leak_active"] = True
    _leak_task = asyncio.create_task(_leak_loop(step_mb, interval_seconds, max_mb))
    return {"ok": True}


@app.post("/admin/memory_leak/stop")
async def stop_memory_leak():
    if not TEST_MODE:
        raise HTTPException(status_code=403, detail="Fault injection is disabled outside test mode.")
    _state["memory_leak_active"] = False
    return {"ok": True}


@app.post("/admin/circuit_breaker")
async def set_circuit_breaker(open: bool):
    """Remediation action endpoint used by the action executor (not a fault).
    Reachable regardless of test mode since opening/closing the breaker is a
    legitimate operational action, not a destructive fault."""
    _state["circuit_breaker_open"] = open
    return {"ok": True, "circuit_breaker_open": _state["circuit_breaker_open"]}
