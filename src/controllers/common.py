"""Shared diagnostic logic used by BOTH the rule-based and AI-driven
controllers. Keeping this identical across the two conditions is what makes
the Section 11 ablation meaningful: any difference in outcomes between
rule-based and AI-driven comes from the trigger (threshold vs. learned
anomaly score + diagnostics), not from a different action policy.

Anomaly detection alone never selects a disruptive action (Section 9): the
caller must combine it with these diagnostics first.
"""
from __future__ import annotations

from collections.abc import Callable

import httpx

from src.app.telemetry import TelemetryRecord
from src.controllers.types import Action, ActionDecision


def count_consecutive_tail(history: list[TelemetryRecord], predicate: Callable[[TelemetryRecord], bool]) -> int:
    count = 0
    for record in reversed(history):
        if predicate(record):
            count += 1
        else:
            break
    return count


def dependency_probe_healthy(dependency_base_url: str, timeout_seconds: float = 1.5) -> bool:
    try:
        r = httpx.get(f"{dependency_base_url}/ping", timeout=timeout_seconds)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def classify_crash(history: list[TelemetryRecord], thresholds: dict) -> ActionDecision | None:
    """Hard-failure check: an unreachable process is directly observable from
    the health check alone and does not require (and cannot use, since no
    resource telemetry exists once the process is down) anomaly scoring."""
    if not history:
        return None
    down_streak = count_consecutive_tail(history, lambda r: not r.health_reachable)
    if down_streak >= thresholds["health_fail_streak"]:
        return ActionDecision(
            action=Action.RESTART_WORKER,
            reason=f"health check unreachable for {down_streak} consecutive polls",
            diagnostics={"down_streak": down_streak},
        )
    return None


def classify_degradation(history: list[TelemetryRecord], thresholds: dict) -> ActionDecision | None:
    """Memory-leak and dependency-timeout diagnostics only (process is alive
    and reporting telemetry). Shared verbatim by rule_based and ai_controller
    so the two conditions differ only in how they decide to LOOK for a cause,
    not in what they do once they find one."""
    if not history:
        return None
    latest = history[-1]

    if latest.health_reachable and latest.mem_mb is not None:
        mem_streak = count_consecutive_tail(
            history, lambda r: r.mem_mb is not None and r.mem_mb > thresholds["mem_mb_threshold"]
        )
        if mem_streak >= thresholds["mem_fail_streak"]:
            return ActionDecision(
                action=Action.RESTART_WORKER,
                reason=f"memory {latest.mem_mb:.1f}MB above {thresholds['mem_mb_threshold']}MB for {mem_streak} consecutive polls",
                diagnostics={"mem_streak": mem_streak, "mem_mb": latest.mem_mb},
            )

    if not latest.circuit_breaker_open:
        dep_fail_streak = count_consecutive_tail(
            history,
            lambda r: (not r.work_success)
            or (r.work_latency_ms is not None and r.work_latency_ms > thresholds["latency_threshold_ms"]),
        )
        if dep_fail_streak >= thresholds["dependency_fail_streak"]:
            return ActionDecision(
                action=Action.OPEN_CIRCUIT_BREAKER,
                reason=f"work requests failing/slow for {dep_fail_streak} consecutive polls",
                diagnostics={"dependency_fail_streak": dep_fail_streak},
            )

    return None


def classify_cause(history: list[TelemetryRecord], thresholds: dict) -> ActionDecision | None:
    """Full diagnostic check (crash, then memory/dependency degradation).
    Used by rule_based.py, which always has live process access to check."""
    return classify_crash(history, thresholds) or classify_degradation(history, thresholds)


def maybe_attempt_breaker_close(history: list[TelemetryRecord], dependency_base_url: str, thresholds: dict) -> ActionDecision | None:
    latest = history[-1] if history else None
    if latest is None or not latest.circuit_breaker_open:
        return None
    if dependency_probe_healthy(dependency_base_url):
        return ActionDecision(action=Action.CLOSE_CIRCUIT_BREAKER, reason="dependency probe succeeded", diagnostics={})
    return ActionDecision(action=Action.NO_ACTION, reason="circuit breaker open, dependency still unhealthy", diagnostics={})
