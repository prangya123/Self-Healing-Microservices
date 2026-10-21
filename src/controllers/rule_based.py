"""Condition B: rule-based self-healing.

Explicit, configurable thresholds (config.yaml -> controller_thresholds) and
deterministic recovery rules. No trained anomaly detector is involved.
"""
from __future__ import annotations

from src.app.telemetry import TelemetryRecord
from src.controllers.common import classify_cause, maybe_attempt_breaker_close
from src.controllers.types import Action, ActionDecision


def decide(history: list[TelemetryRecord], thresholds: dict, dependency_base_url: str) -> ActionDecision:
    if not history:
        return ActionDecision(Action.NO_ACTION, "no telemetry yet")

    breaker_decision = maybe_attempt_breaker_close(history, dependency_base_url, thresholds)
    if breaker_decision is not None:
        return breaker_decision

    decision = classify_cause(history, thresholds)
    if decision is not None:
        return decision

    return ActionDecision(Action.NO_ACTION, "all thresholds nominal")
