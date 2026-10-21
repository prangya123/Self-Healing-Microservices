"""Shared types for controllers, the action executor, and the experiment runner."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Condition(str, Enum):
    BASELINE = "baseline"
    RULE_BASED = "rule_based"
    AI_DRIVEN = "ai_driven"


class Scenario(str, Enum):
    CONTAINER_CRASH = "container_crash"
    MEMORY_LEAK = "memory_leak"
    DEPENDENCY_TIMEOUT = "dependency_timeout"


class Action(str, Enum):
    NO_ACTION = "no_action"
    RESTART_WORKER = "restart_worker"
    OPEN_CIRCUIT_BREAKER = "open_circuit_breaker"
    CLOSE_CIRCUIT_BREAKER = "close_circuit_breaker"
    LOG_INCIDENT = "log_incident"  # cause uncertain: log, do not act


@dataclass
class ActionDecision:
    action: Action
    reason: str
    diagnostics: dict = field(default_factory=dict)


@dataclass
class RunRecord:
    run_id: str
    scenario: str
    condition: str
    seed: int
    workload_config: dict
    fault_injection_timestamp: float | None = None
    detection_timestamp: float | None = None
    action_timestamp: float | None = None
    recovery_timestamp: float | None = None
    recovery_succeeded: bool | None = None
    manual_intervention_required: bool = False
    actions_taken: list = field(default_factory=list)
    degraded_operation_seconds: float = 0.0
    n_requests_total: int = 0
    n_requests_successful: int = 0
    controller_decision_latency_ms_mean: float | None = None
    anomaly_score_trace: list = field(default_factory=list)  # [{"t": wall_time, "score": float}], AI-driven only
    notes: list = field(default_factory=list)
