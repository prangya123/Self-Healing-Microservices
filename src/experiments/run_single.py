"""Runs ONE controlled local fault experiment end-to-end against real,
locally running processes (Section 6C: controlled local fault experiments --
not dataset replay, not simulation). Returns a RunRecord plus the raw
telemetry so the caller can aggregate across repeats.
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid

import httpx

from src.app.telemetry import TelemetryCollector, TelemetryRecord
from src.common.config import load_config, resolve_path
from src.controllers import ai_controller, baseline, rule_based
from src.controllers.action_executor import ActionExecutor
from src.controllers.local_detector import load_local_detector
from src.controllers.types import Action, ActionDecision, Condition, RunRecord, Scenario
from src.experiments.process_manager import ManagedProcess


def _inject_fault(scenario: Scenario, app: ManagedProcess, dependency_base_url: str, app_base_url: str, fault_cfg: dict) -> None:
    if scenario == Scenario.CONTAINER_CRASH:
        app.kill()
    elif scenario == Scenario.MEMORY_LEAK:
        httpx.post(
            f"{app_base_url}/admin/memory_leak/start",
            params={
                "step_mb": fault_cfg["allocation_step_mb"],
                "interval_seconds": fault_cfg["allocation_interval_seconds"],
                "max_mb": fault_cfg["max_allocation_mb"],
            },
            timeout=5.0,
        )
    elif scenario == Scenario.DEPENDENCY_TIMEOUT:
        httpx.post(
            f"{dependency_base_url}/admin/inject_timeout",
            params={
                "enabled": True,
                "delay_seconds": fault_cfg["injected_delay_seconds"],
                "failure_rate": fault_cfg["failure_rate"],
            },
            timeout=5.0,
        )


def _clear_dependency_fault(dependency_base_url: str) -> None:
    httpx.post(f"{dependency_base_url}/admin/inject_timeout", params={"enabled": False}, timeout=5.0)


def _scenario_fault_effect_present(scenario: Scenario, record: TelemetryRecord) -> bool:
    """Objective, condition-independent evidence that the injected fault is
    currently affecting the process -- used only to gate when "recovery" can
    start being evaluated, so an unnoticed, sub-threshold fault effect isn't
    scored as an instant, costless recovery."""
    if scenario == Scenario.CONTAINER_CRASH:
        return not record.health_reachable
    if scenario == Scenario.MEMORY_LEAK:
        return record.leaked_mb is not None and record.leaked_mb > 0
    if scenario == Scenario.DEPENDENCY_TIMEOUT:
        return not record.work_success
    return False


def _action_precondition_met(scenario: Scenario, actions_taken: list[dict]) -> bool:
    """For memory_leak, elevated memory alone never fails a generic health or
    work check (that is only true once resource exhaustion is simulated at a
    much higher ceiling) -- so a worker that is simply left running with a
    growing leak would otherwise look "recovered" by accident. Require that a
    restart actually happened before calling a memory_leak run recovered."""
    if scenario == Scenario.MEMORY_LEAK:
        return any(a["action"] == Action.RESTART_WORKER.value for a in actions_taken)
    return True


def _recovery_satisfied(recent: list[TelemetryRecord], recovery_cfg: dict) -> bool:
    n_health = recovery_cfg["consecutive_successful_health_checks_required"]
    n_work = recovery_cfg["consecutive_successful_work_requests_required"]
    n = max(n_health, n_work)
    if len(recent) < n:
        return False
    tail = recent[-n:]
    healthy = all(r.health_reachable for r in tail[-n_health:])
    # "normal" mode required, not degraded_fallback, per Section 9 (fallback != full recovery)
    working = all(r.work_success and r.work_mode == "normal" for r in tail[-n_work:])
    return healthy and working


def run_single_experiment(
    scenario: Scenario,
    condition: Condition,
    seed: int,
    run_id: str | None = None,
    enable_real_actions: bool = False,
) -> tuple[RunRecord, list[dict]]:
    cfg = load_config()
    random.seed(seed)
    run_id = run_id or f"{scenario.value}_{condition.value}_{seed}_{uuid.uuid4().hex[:8]}"

    app_cfg = cfg["application"]
    app_base_url = f"http://{app_cfg['host']}:{app_cfg['app_port']}"
    dependency_base_url = f"http://{app_cfg['host']}:{app_cfg['dependency_port']}"

    dependency = ManagedProcess(
        "dependency", "src.app.dependency_service:app", app_cfg["dependency_port"],
        extra_env={"SELF_HEALING_TEST_MODE": "1"},
    )
    memory_leak_cfg = next(f for f in cfg["fault_scenarios"] if f["name"] == "memory_leak")
    app_process = ManagedProcess(
        "demo_app_worker", "src.app.main_service:app", app_cfg["app_port"],
        extra_env={
            "SELF_HEALING_TEST_MODE": "1",
            "DEPENDENCY_URL": dependency_base_url,
            "MEMORY_LEAK_HARD_FAILURE_MB": str(memory_leak_cfg["hard_failure_mem_mb"]),
        },
    )

    record = RunRecord(
        run_id=run_id,
        scenario=scenario.value,
        condition=condition.value,
        seed=seed,
        workload_config={"request_rate_per_second": 1.0 / app_cfg["telemetry_interval_seconds"]},
    )

    try:
        dependency.start()
        if not dependency.wait_until_healthy(timeout_seconds=10.0):
            record.notes.append("dependency process failed to become healthy")
            record.recovery_succeeded = False
            record.manual_intervention_required = True
            return record, []

        app_process.start()
        if not app_process.wait_until_healthy(timeout_seconds=10.0):
            record.notes.append("app process failed to become healthy")
            record.recovery_succeeded = False
            record.manual_intervention_required = True
            return record, []

        collector = TelemetryCollector(app_base_url, request_timeout_seconds=app_cfg["telemetry_interval_seconds"] * 2)
        interval = app_cfg["telemetry_interval_seconds"]

        det_cfg = cfg["model"]["local_app_detector"]
        # Only fills the live feature-history buffer (lag/rolling windows)
        # before scoring can start -- no training happens from this. The AI
        # detector itself is trained once, offline, on a pooled corpus (see
        # src/controllers/collect_normal_telemetry.py), not per run.
        n_warmup_polls = max(int(det_cfg["live_warmup_seconds"] / interval), det_cfg["lookback_window"] + 2)
        for _ in range(n_warmup_polls):
            collector.poll_once()
            time.sleep(interval)

        ai_model = ai_scaler = ai_feature_cols = None
        ai_threshold = None
        if condition == Condition.AI_DRIVEN:
            ai_model, ai_scaler, ai_meta = load_local_detector()
            ai_feature_cols = ai_meta["feature_names"]
            ai_threshold = ai_meta["threshold"]
            record.notes.append(
                f"using fixed local AI detector trained on {ai_meta['n_training_rows']} rows "
                f"pooled across {ai_meta['n_sessions']} independent normal-operation sessions"
            )

        executor = ActionExecutor(run_id, app_process, app_base_url)
        if enable_real_actions:
            executor.safety["enable_real_actions"] = True
            executor.dry_run = False

        fault_cfg_lookup = {f["name"]: f for f in cfg["fault_scenarios"]}
        fault_cfg = fault_cfg_lookup[scenario.value]

        record.fault_injection_timestamp = time.time()
        _inject_fault(scenario, app_process, dependency_base_url, app_base_url, fault_cfg)

        dependency_clear_deadline = None
        if scenario == Scenario.DEPENDENCY_TIMEOUT:
            dependency_clear_deadline = record.fault_injection_timestamp + fault_cfg["duration_seconds"]

        thresholds = cfg["controller_thresholds"]
        max_wait = cfg["recovery"]["max_wait_seconds"]
        deadline = time.time() + max_wait
        degraded_polls = 0
        incident_observed = False
        last_restart_wall_time: float | None = None
        decision_latencies_ms: list[float] = []

        while time.time() < deadline:
            if dependency_clear_deadline is not None and time.time() >= dependency_clear_deadline:
                _clear_dependency_fault(dependency_base_url)
                dependency_clear_deadline = None

            poll = collector.poll_once()
            if poll.work_mode == "degraded_fallback":
                degraded_polls += 1
            if not incident_observed and _scenario_fault_effect_present(scenario, poll):
                incident_observed = True

            decision_start = time.monotonic()
            if condition == Condition.BASELINE:
                decision = baseline.decide(collector.records)
            elif condition == Condition.RULE_BASED:
                decision = rule_based.decide(collector.records, thresholds, dependency_base_url)
            else:
                decision = ai_controller.decide(
                    collector.records, thresholds, dependency_base_url,
                    ai_model, ai_scaler, ai_feature_cols,
                    cfg["model"]["local_app_detector"]["lookback_window"], ai_threshold,
                )
            decision_latencies_ms.append((time.monotonic() - decision_start) * 1000.0)

            if condition == Condition.AI_DRIVEN and "anomaly_score" in decision.diagnostics:
                record.anomaly_score_trace.append({"t": time.time(), "score": decision.diagnostics["anomaly_score"]})

            if decision.action != Action.NO_ACTION and record.detection_timestamp is None:
                record.detection_timestamp = time.time()

            if decision.action in (Action.RESTART_WORKER, Action.OPEN_CIRCUIT_BREAKER, Action.CLOSE_CIRCUIT_BREAKER):
                executed = executor.execute(decision, service_name="demo_app_worker")
                if executed:
                    record.actions_taken.append({"t": time.time(), "action": decision.action.value, "reason": decision.reason})
                    if record.action_timestamp is None:
                        record.action_timestamp = time.time()
                    if decision.action == Action.RESTART_WORKER:
                        last_restart_wall_time = time.time()
            elif decision.action == Action.LOG_INCIDENT:
                executor.execute(decision, service_name="demo_app_worker")
                record.actions_taken.append({"t": time.time(), "action": "log_incident", "reason": decision.reason})

            # Only telemetry collected AFTER a restart can demonstrate that
            # restart actually fixed things; otherwise a pre-restart poll
            # that happened to still look normal (e.g. a memory leak that
            # hasn't yet broken a generic health/work check) could be reused
            # to falsely confirm recovery the instant the restart fires.
            recovery_candidates = collector.records
            if last_restart_wall_time is not None:
                recovery_candidates = [r for r in collector.records if r.wall_time >= last_restart_wall_time]

            if (
                incident_observed
                and _action_precondition_met(scenario, record.actions_taken)
                and _recovery_satisfied(recovery_candidates, cfg["recovery"])
            ):
                record.recovery_timestamp = time.time()
                record.recovery_succeeded = True
                break

            time.sleep(interval)

        if record.recovery_timestamp is None:
            record.recovery_succeeded = False
            record.manual_intervention_required = True
            record.notes.append(f"recovery not observed within max_wait_seconds={max_wait}")

        if scenario == Scenario.DEPENDENCY_TIMEOUT:
            _clear_dependency_fault(dependency_base_url)

        record.degraded_operation_seconds = degraded_polls * interval
        record.n_requests_total = len(collector.records)
        record.n_requests_successful = sum(1 for r in collector.records if r.work_success)
        if decision_latencies_ms:
            record.controller_decision_latency_ms_mean = sum(decision_latencies_ms) / len(decision_latencies_ms)

        return record, collector.to_dicts()

    finally:
        app_process.kill()
        dependency.kill()


def save_run(record: RunRecord, telemetry: list[dict]) -> str:
    cfg = load_config()
    logs_dir = resolve_path(cfg["paths"]["results_logs"])
    runs_dir = os.path.join(logs_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    path = os.path.join(runs_dir, f"{record.run_id}.json")
    with open(path, "w") as f:
        json.dump({"run_record": record.__dict__, "telemetry": telemetry}, f, indent=2, default=str)
    return path
