"""Condition C: AI-driven self-healing.

A trained anomaly detector scores live telemetry; an interpretable decision
layer (the SAME classify_cause() diagnostics used by the rule-based
controller) picks the remediation action. The anomaly score only GATES
whether to look for a cause at all -- it never selects the action by itself
(Section 9). When the score is elevated but no specific cause is supported
by the diagnostics, the incident is logged rather than acted on.

Sharing classify_cause() with rule_based.py is deliberate: it isolates the
experimental comparison to "learned trigger vs. threshold trigger" rather
than confounding it with a different action policy (Section 11 ablation).
"""
from __future__ import annotations

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.app.telemetry import TelemetryRecord
from src.controllers.common import classify_crash, classify_degradation, maybe_attempt_breaker_close
from src.controllers.local_features import latest_feature_vector
from src.controllers.types import Action, ActionDecision


def decide(
    history: list[TelemetryRecord],
    thresholds: dict,
    dependency_base_url: str,
    model: IsolationForest,
    scaler: StandardScaler,
    feature_cols: list[str],
    lookback_window: int,
    frozen_threshold: float,
) -> ActionDecision:
    if not history:
        return ActionDecision(Action.NO_ACTION, "no telemetry yet")

    breaker_decision = maybe_attempt_breaker_close(history, dependency_base_url, thresholds)
    if breaker_decision is not None:
        return breaker_decision

    # A dead process is directly observable from the health check and has no
    # resource telemetry to score -- check this before (not via) the anomaly
    # detector, consistent with "health checks before disruptive actions".
    crash_decision = classify_crash(history, thresholds)
    if crash_decision is not None:
        return crash_decision

    x = latest_feature_vector(history, lookback_window, feature_cols)
    if x is None:
        return ActionDecision(Action.NO_ACTION, "insufficient history for anomaly scoring")

    x_scaled = scaler.transform(x)
    score = float(-model.decision_function(x_scaled)[0])

    if score <= frozen_threshold:
        return ActionDecision(Action.NO_ACTION, f"anomaly score {score:.3f} below frozen threshold {frozen_threshold:.3f}", {"anomaly_score": score})

    decision = classify_degradation(history, thresholds)
    if decision is not None:
        decision.diagnostics["anomaly_score"] = score
        return decision

    return ActionDecision(
        action=Action.LOG_INCIDENT,
        reason=f"anomaly score {score:.3f} exceeded threshold {frozen_threshold:.3f} but no specific cause was supported by diagnostics",
        diagnostics={"anomaly_score": score},
    )
