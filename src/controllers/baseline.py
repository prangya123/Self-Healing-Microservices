"""Condition A: baseline.

Default health-check-only behavior. No configurable thresholds for memory or
dependency latency, no learned anomaly detection, no circuit breaker. This
intentionally represents a naive "restart on failed health check" default
and nothing else, so its shortcomings (e.g. never reacting to a slow
dependency) are a real, reportable finding rather than something tuned away.
"""
from __future__ import annotations

from src.app.telemetry import TelemetryRecord
from src.controllers.common import count_consecutive_tail
from src.controllers.types import Action, ActionDecision

BASELINE_HEALTH_FAIL_STREAK = 1


def decide(history: list[TelemetryRecord]) -> ActionDecision:
    if not history:
        return ActionDecision(Action.NO_ACTION, "no telemetry yet")

    down_streak = count_consecutive_tail(history, lambda r: not r.health_reachable)
    if down_streak >= BASELINE_HEALTH_FAIL_STREAK:
        return ActionDecision(
            action=Action.RESTART_WORKER,
            reason=f"default health check unreachable for {down_streak} consecutive polls",
            diagnostics={"down_streak": down_streak},
        )
    return ActionDecision(Action.NO_ACTION, "health check passing")
