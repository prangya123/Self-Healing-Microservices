"""Trains and loads the IsolationForest used by the AI-driven controller.

Trained ONCE, offline, on a pooled corpus of normal-operation telemetry
collected across several independent sessions (src/controllers/
collect_normal_telemetry.py), then frozen and reused across all experiment
runs -- the same pattern used for the Microsoft/Kaggle offline detectors.
Sessions are kept separate during feature engineering (each session's
lag/rolling features only look backward within that session) and only pooled
afterward, so no session's features leak across a session boundary.
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.app.telemetry import TelemetryRecord
from src.common.config import load_config, resolve_path
from src.controllers.local_features import build_feature_frame

MODEL_SUBDIR = "local_app"


def train_local_detector_from_sessions(sessions: list[list[TelemetryRecord]]) -> dict:
    cfg = load_config()
    det_cfg = cfg["model"]["local_app_detector"]
    lookback = det_cfg["lookback_window"]

    per_session_frames = []
    feature_cols: list[str] | None = None
    for session_history in sessions:
        df, cols = build_feature_frame(session_history, lookback)
        feature_cols = cols
        per_session_frames.append(df.dropna(subset=cols))

    pooled = pd.concat(per_session_frames, ignore_index=True)
    if len(pooled) < 20:
        raise ValueError(
            f"Only {len(pooled)} usable training rows pooled across {len(sessions)} session(s) "
            f"after dropping incomplete lag/rolling windows; increase "
            f"model.local_app_detector.training_sessions / training_session_seconds in config.yaml."
        )

    X = pooled[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=det_cfg["n_estimators"],
        random_state=det_cfg["random_state"],
    )
    model.fit(X_scaled)

    scores = -model.decision_function(X_scaled)
    threshold = float(np.percentile(scores, det_cfg["threshold_percentile"]))

    models_dir = resolve_path(cfg["paths"]["models_dir"])
    out_dir = os.path.join(models_dir, MODEL_SUBDIR)
    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(model, os.path.join(out_dir, "isolation_forest.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "scaler.joblib"))

    metadata = {
        "dataset_identifier": "local_app_telemetry_pooled_normal_sessions",
        "feature_names": feature_cols,
        "lookback_window": lookback,
        "n_sessions": len(sessions),
        "n_training_rows": len(pooled),
        "threshold": threshold,
        "threshold_percentile": det_cfg["threshold_percentile"],
        "threshold_method": "percentile_of_training_scores_no_labels",
        "random_seed": det_cfg["random_state"],
        "model_type": "sklearn.ensemble.IsolationForest",
        "notes": [
            f"Trained once on {len(sessions)} independent normal-operation telemetry sessions "
            f"({len(pooled)} rows pooled), each from a freshly started application instance -- "
            "NOT retrained per experiment run.",
            "No fault labels exist for this telemetry; threshold is NOT F1-tuned (unlike the offline datasets).",
            "Superseded the original per-run warmup design after it was found to be unreliable "
            "(see results/reports/limitations_report.md item 8).",
        ],
    }
    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    return metadata


def load_local_detector() -> tuple[IsolationForest, StandardScaler, dict]:
    cfg = load_config()
    out_dir = os.path.join(resolve_path(cfg["paths"]["models_dir"]), MODEL_SUBDIR)
    model_path = os.path.join(out_dir, "isolation_forest.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            "No local AI detector found. Run `python3 -m src.controllers.collect_normal_telemetry` "
            "once before running AI-driven experiments."
        )
    model = joblib.load(model_path)
    scaler = joblib.load(os.path.join(out_dir, "scaler.joblib"))
    with open(os.path.join(out_dir, "metadata.json")) as f:
        metadata = json.load(f)
    return model, scaler, metadata
