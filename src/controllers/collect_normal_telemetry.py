"""Builds the FIXED local-app AI detector (run once, offline, before AI-driven
experiments) by collecting several independent sessions of normal-operation
telemetry -- no fault is ever injected during this collection.

Each session starts a fresh app+dependency process pair (so the pooled
training data includes realistic process-startup variation, since that is
also what every experiment run's live scoring sees at its own start) and
polls for `training_session_seconds`. Sessions are kept separate during
feature engineering so lag/rolling windows never cross a session boundary.

Usage:
    python3 -m src.controllers.collect_normal_telemetry
"""
from __future__ import annotations

import time

from src.app.telemetry import TelemetryCollector
from src.common.config import load_config
from src.controllers.local_detector import train_local_detector_from_sessions
from src.experiments.process_manager import ManagedProcess


def collect_one_session(session_seconds: float, interval: float, app_cfg: dict) -> list:
    dependency = ManagedProcess(
        "dependency", "src.app.dependency_service:app", app_cfg["dependency_port"],
        extra_env={"SELF_HEALING_TEST_MODE": "1"},
    )
    app_process = ManagedProcess(
        "demo_app_worker", "src.app.main_service:app", app_cfg["app_port"],
        extra_env={
            "SELF_HEALING_TEST_MODE": "1",
            "DEPENDENCY_URL": f"http://{app_cfg['host']}:{app_cfg['dependency_port']}",
        },
    )
    try:
        dependency.start()
        dependency.wait_until_healthy(timeout_seconds=10.0)
        app_process.start()
        app_process.wait_until_healthy(timeout_seconds=10.0)

        collector = TelemetryCollector(f"http://{app_cfg['host']}:{app_cfg['app_port']}", request_timeout_seconds=interval * 2)
        deadline = time.time() + session_seconds
        while time.time() < deadline:
            collector.poll_once()
            time.sleep(interval)
        return collector.records
    finally:
        app_process.kill()
        dependency.kill()


def main() -> None:
    cfg = load_config()
    app_cfg = cfg["application"]
    det_cfg = cfg["model"]["local_app_detector"]
    interval = app_cfg["telemetry_interval_seconds"]

    sessions = []
    for i in range(det_cfg["training_sessions"]):
        print(f"Collecting normal-operation session {i + 1}/{det_cfg['training_sessions']} "
              f"({det_cfg['training_session_seconds']}s, no fault injected)...")
        records = collect_one_session(det_cfg["training_session_seconds"], interval, app_cfg)
        print(f"  collected {len(records)} telemetry rows")
        sessions.append(records)

    metadata = train_local_detector_from_sessions(sessions)
    print(f"\nTrained local AI detector on {metadata['n_training_rows']} pooled rows "
          f"across {metadata['n_sessions']} sessions.")
    print(f"Threshold (p{metadata['threshold_percentile']} of training scores): {metadata['threshold']:.4f}")
    print("Saved to models/local_app/ (isolation_forest.joblib, scaler.joblib, metadata.json)")


if __name__ == "__main__":
    main()
