"""Stage 6: aggregates all saved run records (results/logs/runs/*.json) into
one analysis-ready table. No run is silently excluded, including unrecovered
or failed ones (Section 12).
"""
from __future__ import annotations

import glob
import json
import os

import pandas as pd

from src.common.config import load_config, resolve_path


def _load_run_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def load_all_runs() -> pd.DataFrame:
    cfg = load_config()
    runs_dir = os.path.join(resolve_path(cfg["paths"]["results_logs"]), "runs")
    paths = sorted(glob.glob(os.path.join(runs_dir, "*.json")))

    rows = []
    for path in paths:
        data = _load_run_json(path)
        r = data["run_record"]

        detection_delay_s = None
        if r.get("fault_injection_timestamp") and r.get("detection_timestamp"):
            detection_delay_s = r["detection_timestamp"] - r["fault_injection_timestamp"]

        action_delay_s = None
        if r.get("detection_timestamp") and r.get("action_timestamp"):
            action_delay_s = r["action_timestamp"] - r["detection_timestamp"]

        mttr_s = None
        if r.get("fault_injection_timestamp") and r.get("recovery_timestamp"):
            mttr_s = r["recovery_timestamp"] - r["fault_injection_timestamp"]

        detection_to_recovery_s = None
        if r.get("detection_timestamp") and r.get("recovery_timestamp"):
            detection_to_recovery_s = r["recovery_timestamp"] - r["detection_timestamp"]

        actions = r.get("actions_taken") or []
        n_restart = sum(1 for a in actions if a["action"] == "restart_worker")
        n_breaker_open = sum(1 for a in actions if a["action"] == "open_circuit_breaker")
        n_breaker_close = sum(1 for a in actions if a["action"] == "close_circuit_breaker")
        n_log_incident = sum(1 for a in actions if a["action"] == "log_incident")
        excess_actions = max(0, n_restart - 1) + max(0, n_breaker_open - 1)

        n_total = r.get("n_requests_total") or 0
        n_success = r.get("n_requests_successful") or 0
        request_success_rate = (n_success / n_total) if n_total else None

        rows.append(
            {
                "run_id": r["run_id"],
                "scenario": r["scenario"],
                "condition": r["condition"],
                "seed": r["seed"],
                "recovery_succeeded": r.get("recovery_succeeded"),
                "manual_intervention_required": r.get("manual_intervention_required"),
                "detection_delay_s": detection_delay_s,
                "action_delay_s": action_delay_s,
                "mttr_s": mttr_s,
                "detection_to_recovery_s": detection_to_recovery_s,
                "n_actions_taken": len(actions),
                "n_restart_actions": n_restart,
                "n_breaker_open_actions": n_breaker_open,
                "n_breaker_close_actions": n_breaker_close,
                "n_log_incident_actions": n_log_incident,
                "excess_actions": excess_actions,
                "degraded_operation_seconds": r.get("degraded_operation_seconds"),
                "n_requests_total": n_total,
                "n_requests_successful": n_success,
                "request_success_rate": request_success_rate,
                "controller_decision_latency_ms_mean": r.get("controller_decision_latency_ms_mean"),
                "notes": "; ".join(r.get("notes") or []),
                "source_path": path,
            }
        )

    return pd.DataFrame(rows)


def save_runs_table(df: pd.DataFrame) -> str:
    cfg = load_config()
    tables_dir = resolve_path(cfg["paths"]["results_tables"])
    os.makedirs(tables_dir, exist_ok=True)
    path = os.path.join(tables_dir, "experiment_runs.csv")
    df.to_csv(path, index=False)
    return path


def build_summary_by_condition_scenario(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def agg(group: pd.DataFrame) -> pd.Series:
        n = len(group)
        recovered = group["recovery_succeeded"].fillna(False)
        return pd.Series(
            {
                "n_runs": n,
                "recovery_success_rate": recovered.mean(),
                "n_unrecovered": int((~recovered).sum()),
                "n_manual_intervention_required": int(group["manual_intervention_required"].fillna(False).sum()),
                "mttr_mean_s": group["mttr_s"].mean(),
                "mttr_median_s": group["mttr_s"].median(),
                "mttr_std_s": group["mttr_s"].std(),
                "detection_delay_mean_s": group["detection_delay_s"].mean(),
                "detection_delay_median_s": group["detection_delay_s"].median(),
                "request_success_rate_mean": group["request_success_rate"].mean(),
                "degraded_operation_seconds_mean": group["degraded_operation_seconds"].mean(),
                "excess_actions_mean": group["excess_actions"].mean(),
            }
        )

    summary = df.groupby(["scenario", "condition"]).apply(agg, include_groups=False).reset_index()
    return summary


def save_summary_table(summary: pd.DataFrame) -> str:
    cfg = load_config()
    tables_dir = resolve_path(cfg["paths"]["results_tables"])
    os.makedirs(tables_dir, exist_ok=True)
    path = os.path.join(tables_dir, "summary_by_condition_scenario.csv")
    summary.to_csv(path, index=False)
    return path


def main() -> None:
    df = load_all_runs()
    runs_path = save_runs_table(df)
    print(f"Wrote {len(df)} runs to {runs_path}")
    if df.empty:
        print("No runs found yet -- run src.experiments.runner first.")
        return
    summary = build_summary_by_condition_scenario(df)
    summary_path = save_summary_table(summary)
    print(f"Wrote summary to {summary_path}")
    print(summary.to_string())


if __name__ == "__main__":
    main()
