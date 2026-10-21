"""Small dependency service used by the main app's /work endpoint.

Fault injection (dependency timeout) is only reachable when the process is
started with SELF_HEALING_TEST_MODE=1 in its environment. This is a real,
separately-running process (not a mock) so that timeouts are observed as
actual network-level delays by the caller.
"""
from __future__ import annotations

import asyncio
import os
import random
import time

from fastapi import FastAPI, HTTPException

TEST_MODE = os.environ.get("SELF_HEALING_TEST_MODE") == "1"

app = FastAPI(title="dependency-service")

_state = {
    "timeout_injected": False,
    "injected_delay_seconds": 0.0,
    "failure_rate": 0.0,
}


@app.get("/health")
async def health():
    return {"status": "ok", "test_mode": TEST_MODE}


@app.get("/ping")
async def ping():
    start = time.monotonic()
    if _state["timeout_injected"]:
        await asyncio.sleep(_state["injected_delay_seconds"])
        if random.random() < _state["failure_rate"]:
            raise HTTPException(status_code=503, detail="injected dependency failure")
    latency_ms = (time.monotonic() - start) * 1000.0
    return {"status": "ok", "latency_ms": latency_ms}


@app.post("/admin/inject_timeout")
async def inject_timeout(enabled: bool, delay_seconds: float = 0.0, failure_rate: float = 0.0):
    if not TEST_MODE:
        raise HTTPException(status_code=403, detail="Fault injection is disabled outside test mode.")
    _state["timeout_injected"] = enabled
    _state["injected_delay_seconds"] = delay_seconds
    _state["failure_rate"] = failure_rate
    return {"ok": True, "state": _state}


@app.get("/admin/state")
async def admin_state():
    if not TEST_MODE:
        raise HTTPException(status_code=403, detail="Admin introspection is disabled outside test mode.")
    return _state
