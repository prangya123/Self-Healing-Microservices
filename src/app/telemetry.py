"""Polls the running application and dependency over real HTTP and records
structured telemetry rows. This is live, measured telemetry from the local
testbed -- not a simulation and not historical dataset replay.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict

import httpx


@dataclass
class TelemetryRecord:
    t: float  # monotonic seconds since collector start
    wall_time: float  # time.time()
    health_reachable: bool
    cpu_percent: float | None
    mem_mb: float | None
    circuit_breaker_open: bool | None
    leaked_mb: float | None
    work_success: bool
    work_latency_ms: float | None
    work_mode: str | None  # "normal" | "degraded_fallback" | None (request failed)


class TelemetryCollector:
    def __init__(self, app_base_url: str, request_timeout_seconds: float = 2.0):
        self.app_base_url = app_base_url
        self.request_timeout_seconds = request_timeout_seconds
        self.records: list[TelemetryRecord] = []
        self._start_monotonic = time.monotonic()

    def poll_once(self) -> TelemetryRecord:
        health_reachable = False
        cpu_percent = mem_mb = circuit_breaker_open = leaked_mb = None
        try:
            r = httpx.get(f"{self.app_base_url}/health", timeout=self.request_timeout_seconds)
            if r.status_code == 200:
                health_reachable = True
                body = r.json()
                cpu_percent = body.get("cpu_percent")
                mem_mb = body.get("mem_mb")
                circuit_breaker_open = body.get("circuit_breaker_open")
                leaked_mb = body.get("leaked_mb")
        except httpx.HTTPError:
            pass

        work_success = False
        work_latency_ms = None
        work_mode = None
        start = time.monotonic()
        try:
            r = httpx.get(f"{self.app_base_url}/work", timeout=self.request_timeout_seconds)
            work_latency_ms = (time.monotonic() - start) * 1000.0
            if r.status_code == 200:
                work_success = True
                work_mode = r.json().get("mode")
        except httpx.HTTPError:
            work_latency_ms = (time.monotonic() - start) * 1000.0

        record = TelemetryRecord(
            t=time.monotonic() - self._start_monotonic,
            wall_time=time.time(),
            health_reachable=health_reachable,
            cpu_percent=cpu_percent,
            mem_mb=mem_mb,
            circuit_breaker_open=circuit_breaker_open,
            leaked_mb=leaked_mb,
            work_success=work_success,
            work_latency_ms=work_latency_ms,
            work_mode=work_mode,
        )
        self.records.append(record)
        return record

    def to_dicts(self) -> list[dict]:
        return [asdict(r) for r in self.records]
