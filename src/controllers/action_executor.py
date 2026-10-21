"""Guarded remediation executor.

Safety defaults (Section 10):
- Dry-run unless safety.enable_real_actions is explicitly true in config.yaml.
- Only services on the allowlist can be targeted.
- Actions are rate-limited by cooldown, a per-run cap, and a restart cap.
- A stop-switch file immediately halts all further actions.
- Every decision (executed or not) is written to a structured audit log.
- No shell commands are ever constructed from telemetry/model/dataset content:
  the only operations performed are kill/restart a named, allowlisted
  subprocess, or call a fixed, parameterless admin HTTP endpoint.
"""
from __future__ import annotations

import json
import os
import time

import httpx

from src.common.config import load_config, resolve_path
from src.controllers.types import Action, ActionDecision
from src.experiments.process_manager import ManagedProcess


class ActionExecutor:
    def __init__(self, run_id: str, app_process: ManagedProcess, app_base_url: str):
        cfg = load_config()
        self.safety = cfg["safety"]
        self.run_id = run_id
        self.app_process = app_process
        self.app_base_url = app_base_url

        self.dry_run = self.safety["dry_run_default"] and not self.safety["enable_real_actions"]
        self._last_action_time: float | None = None
        self._actions_this_run = 0
        self._restarts_this_run = 0

        logs_dir = resolve_path(cfg["paths"]["results_logs"])
        os.makedirs(logs_dir, exist_ok=True)
        self.audit_log_path = os.path.join(logs_dir, f"audit_{run_id}.jsonl")

    def _stop_switch_engaged(self) -> bool:
        return os.path.exists(resolve_path(self.safety["stop_switch_file"]))

    def _audit(self, event: str, **fields) -> None:
        record = {"ts": time.time(), "run_id": self.run_id, "event": event, **fields}
        with open(self.audit_log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _cooldown_elapsed(self) -> bool:
        if self._last_action_time is None:
            return True
        return (time.time() - self._last_action_time) >= self.safety["action_cooldown_seconds"]

    def execute(self, decision: ActionDecision, service_name: str) -> bool:
        """Returns True if the action was actually executed, False if blocked
        or skipped (dry-run, cooldown, cap, allowlist, stop switch)."""
        if self._stop_switch_engaged():
            self._audit("blocked_stop_switch", action=decision.action, reason=decision.reason)
            return False

        if decision.action == Action.NO_ACTION:
            return False

        if decision.action == Action.LOG_INCIDENT:
            self._audit("incident_logged", reason=decision.reason, diagnostics=decision.diagnostics)
            return False

        if service_name not in self.safety["service_allowlist"]:
            self._audit("blocked_not_allowlisted", service=service_name, action=decision.action)
            return False

        if self._actions_this_run >= self.safety["max_actions_per_run"]:
            self._audit("blocked_max_actions_per_run", action=decision.action)
            return False

        if decision.action == Action.RESTART_WORKER and self._restarts_this_run >= self.safety["max_restarts_per_run"]:
            self._audit("blocked_max_restarts_per_run", action=decision.action)
            return False

        if not self._cooldown_elapsed():
            self._audit("blocked_cooldown", action=decision.action)
            return False

        if self.dry_run:
            self._audit("dry_run_skipped", action=decision.action, reason=decision.reason, diagnostics=decision.diagnostics)
            self._last_action_time = time.time()
            self._actions_this_run += 1
            return False

        executed = self._perform(decision.action)
        self._audit("executed" if executed else "execute_failed", action=decision.action, reason=decision.reason)
        if executed:
            self._last_action_time = time.time()
            self._actions_this_run += 1
            if decision.action == Action.RESTART_WORKER:
                self._restarts_this_run += 1
        return executed

    def _perform(self, action: Action) -> bool:
        timeout = self.safety["execution_timeout_seconds"]
        try:
            if action == Action.RESTART_WORKER:
                self.app_process.kill()
                self.app_process.start()
                return self.app_process.wait_until_healthy(timeout_seconds=timeout)
            if action == Action.OPEN_CIRCUIT_BREAKER:
                r = httpx.post(f"{self.app_base_url}/admin/circuit_breaker", params={"open": True}, timeout=timeout)
                return r.status_code == 200
            if action == Action.CLOSE_CIRCUIT_BREAKER:
                r = httpx.post(f"{self.app_base_url}/admin/circuit_breaker", params={"open": False}, timeout=timeout)
                return r.status_code == 200
        except (httpx.HTTPError, OSError):
            return False
        return False
