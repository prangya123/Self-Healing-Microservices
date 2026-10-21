import json
import os

import pytest

from src.common.config import load_config, resolve_path
from src.controllers.action_executor import ActionExecutor
from src.controllers.types import Action, ActionDecision


class FakeProcess:
    def __init__(self):
        self.killed = False
        self.started = False

    def kill(self):
        self.killed = True

    def start(self):
        self.started = True

    def wait_until_healthy(self, timeout_seconds=10.0):
        return True


@pytest.fixture
def cfg():
    return load_config()


def _read_audit(executor: ActionExecutor) -> list[dict]:
    with open(executor.audit_log_path) as f:
        return [json.loads(line) for line in f]


def test_dry_run_default_blocks_real_execution(cfg, tmp_path):
    assert cfg["safety"]["dry_run_default"] is True
    assert cfg["safety"]["enable_real_actions"] is False

    proc = FakeProcess()
    executor = ActionExecutor(run_id="test_dry_run", app_process=proc, app_base_url="http://127.0.0.1:1")
    decision = ActionDecision(Action.RESTART_WORKER, "test")
    executed = executor.execute(decision, service_name=cfg["safety"]["service_allowlist"][0])

    assert executed is False
    assert proc.killed is False and proc.started is False
    audit = _read_audit(executor)
    assert any(e["event"] == "dry_run_skipped" for e in audit)


def test_non_allowlisted_service_is_blocked(cfg):
    proc = FakeProcess()
    executor = ActionExecutor(run_id="test_allowlist", app_process=proc, app_base_url="http://127.0.0.1:1")
    decision = ActionDecision(Action.RESTART_WORKER, "test")
    executed = executor.execute(decision, service_name="not_a_real_service")
    assert executed is False
    audit = _read_audit(executor)
    assert any(e["event"] == "blocked_not_allowlisted" for e in audit)


def test_max_actions_per_run_is_enforced(cfg, monkeypatch):
    monkeypatch.setitem(cfg["safety"], "max_actions_per_run", 1)
    proc = FakeProcess()
    executor = ActionExecutor(run_id="test_max_actions", app_process=proc, app_base_url="http://127.0.0.1:1")
    executor.safety["max_actions_per_run"] = 1
    executor.safety["action_cooldown_seconds"] = 0

    decision = ActionDecision(Action.RESTART_WORKER, "test")
    service = executor.safety["service_allowlist"][0]
    executor.execute(decision, service)  # first: dry-run-skipped, but counts toward cap
    executed_second = executor.execute(decision, service)
    assert executed_second is False
    audit = _read_audit(executor)
    assert any(e["event"] == "blocked_max_actions_per_run" for e in audit)


def test_stop_switch_blocks_all_actions(cfg):
    proc = FakeProcess()
    executor = ActionExecutor(run_id="test_stop_switch", app_process=proc, app_base_url="http://127.0.0.1:1")
    stop_path = resolve_path(executor.safety["stop_switch_file"])
    os.makedirs(os.path.dirname(stop_path), exist_ok=True)
    with open(stop_path, "w") as f:
        f.write("stop")
    try:
        decision = ActionDecision(Action.RESTART_WORKER, "test")
        executed = executor.execute(decision, executor.safety["service_allowlist"][0])
        assert executed is False
        audit = _read_audit(executor)
        assert any(e["event"] == "blocked_stop_switch" for e in audit)
    finally:
        os.remove(stop_path)


def test_log_incident_never_touches_process_or_allowlist(cfg):
    proc = FakeProcess()
    executor = ActionExecutor(run_id="test_log_incident", app_process=proc, app_base_url="http://127.0.0.1:1")
    decision = ActionDecision(Action.LOG_INCIDENT, "ambiguous anomaly")
    executed = executor.execute(decision, service_name="anything_even_unlisted")
    assert executed is False
    assert proc.killed is False and proc.started is False
    audit = _read_audit(executor)
    assert any(e["event"] == "incident_logged" for e in audit)
