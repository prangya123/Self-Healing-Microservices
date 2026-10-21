from src.app.telemetry import TelemetryRecord
from src.controllers import ai_controller, baseline, rule_based
from src.controllers.types import Action

THRESHOLDS = {
    "health_fail_streak": 2,
    "mem_mb_threshold": 150.0,
    "mem_fail_streak": 3,
    "dependency_fail_streak": 3,
    "latency_threshold_ms": 1000.0,
}


def _rec(**kwargs) -> TelemetryRecord:
    defaults = dict(
        t=0.0, wall_time=0.0, health_reachable=True, cpu_percent=1.0, mem_mb=50.0,
        circuit_breaker_open=False, leaked_mb=0.0, work_success=True,
        work_latency_ms=10.0, work_mode="normal",
    )
    defaults.update(kwargs)
    return TelemetryRecord(**defaults)


def test_baseline_restarts_on_single_health_failure_but_ignores_memory_growth():
    history = [_rec(health_reachable=False)]
    decision = baseline.decide(history)
    assert decision.action == Action.RESTART_WORKER

    history2 = [_rec(mem_mb=500.0) for _ in range(10)]  # huge memory growth
    decision2 = baseline.decide(history2)
    assert decision2.action == Action.NO_ACTION, "baseline must not react to memory thresholds"


def test_rule_based_restarts_after_health_fail_streak_not_before():
    history = [_rec(), _rec(health_reachable=False)]
    assert rule_based.decide(history, THRESHOLDS, "http://127.0.0.1:1").action == Action.NO_ACTION
    history.append(_rec(health_reachable=False))
    assert rule_based.decide(history, THRESHOLDS, "http://127.0.0.1:1").action == Action.RESTART_WORKER


def test_rule_based_restarts_on_sustained_memory_growth():
    history = [_rec(mem_mb=200.0) for _ in range(3)]
    decision = rule_based.decide(history, THRESHOLDS, "http://127.0.0.1:1")
    assert decision.action == Action.RESTART_WORKER
    assert "memory" in decision.reason


def test_rule_based_opens_circuit_breaker_on_sustained_work_failures():
    history = [_rec(work_success=False) for _ in range(3)]
    decision = rule_based.decide(history, THRESHOLDS, "http://127.0.0.1:1")
    assert decision.action == Action.OPEN_CIRCUIT_BREAKER


def test_ai_controller_logs_incident_when_anomalous_but_cause_unclear(monkeypatch):
    class FakeModel:
        def decision_function(self, X):
            return [-0.9]  # very negative => high anomaly score after sign flip

    class FakeScaler:
        def transform(self, X):
            return X

    # Build enough history for feature extraction (lookback=2) but no
    # threshold-breaching pattern in any of the three specific signals.
    history = [_rec(mem_mb=50.0 + i, work_latency_ms=10.0 + i) for i in range(5)]
    feature_cols = ["mem_mb", "mem_mb__lag1", "mem_mb__roll_mean2", "mem_mb__rate_of_change"]

    import src.controllers.ai_controller as aic
    monkeypatch.setattr(aic, "latest_feature_vector", lambda h, w, cols: [[0.0] * len(cols)])

    decision = ai_controller.decide(
        history, THRESHOLDS, "http://127.0.0.1:1",
        model=FakeModel(), scaler=FakeScaler(), feature_cols=feature_cols,
        lookback_window=2, frozen_threshold=0.1,
    )
    assert decision.action == Action.LOG_INCIDENT
    assert "anomaly_score" in decision.diagnostics


def test_ai_controller_takes_no_action_when_score_below_threshold(monkeypatch):
    class FakeModel:
        def decision_function(self, X):
            return [0.9]  # low anomaly score after sign flip

    class FakeScaler:
        def transform(self, X):
            return X

    history = [_rec()]
    import src.controllers.ai_controller as aic
    monkeypatch.setattr(aic, "latest_feature_vector", lambda h, w, cols: [[0.0]])

    decision = ai_controller.decide(
        history, THRESHOLDS, "http://127.0.0.1:1",
        model=FakeModel(), scaler=FakeScaler(), feature_cols=["x"],
        lookback_window=2, frozen_threshold=0.5,
    )
    assert decision.action == Action.NO_ACTION
