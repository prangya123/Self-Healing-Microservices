"""Isolation Forest anomaly detector with validation-frozen thresholding.

This is a shallow, non-temporal model (scikit-learn's IsolationForest).
Any temporal context comes entirely from the engineered lag/rolling/rate
features built in src/preprocessing/features.py -- this is NOT an LSTM or
any other sequence model, and must never be described as one.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score

from src.common.config import load_config, resolve_path
from src.preprocessing.pipeline import PreparedDataset


@dataclass
class ThresholdSelection:
    method: str
    candidate_percentiles: list
    chosen_percentile: float | None
    chosen_threshold: float
    chosen_val_f1: float | None
    val_has_labels: bool


def anomaly_score(model: IsolationForest, X: np.ndarray) -> np.ndarray:
    """Higher score = more anomalous (sign-flipped from sklearn's convention)."""
    return -model.decision_function(X)


def select_threshold(model: IsolationForest, X_val: np.ndarray, y_val: np.ndarray | None, candidate_percentiles: list[float]) -> ThresholdSelection:
    scores = anomaly_score(model, X_val) if len(X_val) else np.array([])

    if y_val is None or len(y_val) == 0 or len(scores) == 0:
        # No validation labels available: fall back to a conservative default
        # (95th percentile of validation scores) and disclose that it was not
        # label-tuned.
        chosen = float(np.percentile(scores, 95)) if len(scores) else 0.0
        return ThresholdSelection(
            method="label_free_percentile_fallback",
            candidate_percentiles=candidate_percentiles,
            chosen_percentile=95.0,
            chosen_threshold=chosen,
            chosen_val_f1=None,
            val_has_labels=False,
        )

    best_f1 = -1.0
    best_pct = candidate_percentiles[0]
    best_thresh = float(np.percentile(scores, candidate_percentiles[0]))
    for pct in candidate_percentiles:
        thresh = np.percentile(scores, pct)
        preds = (scores > thresh).astype(int)
        f1 = f1_score(y_val, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_pct = pct
            best_thresh = float(thresh)

    return ThresholdSelection(
        method="validation_f1_grid_search",
        candidate_percentiles=candidate_percentiles,
        chosen_percentile=float(best_pct),
        chosen_threshold=best_thresh,
        chosen_val_f1=float(best_f1),
        val_has_labels=True,
    )


def train_and_save(prepared: PreparedDataset, dataset_name: str) -> dict:
    cfg = load_config()
    if_cfg = cfg["model"]["isolation_forest"]
    seed = cfg["random_seed"]

    model = IsolationForest(
        n_estimators=if_cfg["n_estimators"],
        max_samples=if_cfg["max_samples"],
        contamination=if_cfg["contamination"],
        random_state=seed,
    )
    model.fit(prepared.X_train)

    threshold = select_threshold(
        model,
        prepared.X_val,
        prepared.y_val,
        cfg["model"]["threshold_selection"]["candidate_percentiles"],
    )

    models_dir = resolve_path(cfg["paths"]["models_dir"])
    out_dir = os.path.join(models_dir, dataset_name)
    os.makedirs(out_dir, exist_ok=True)

    joblib.dump(model, os.path.join(out_dir, "isolation_forest.joblib"))
    joblib.dump(prepared.scaler, os.path.join(out_dir, "scaler.joblib"))

    metadata = {
        "dataset_identifier": dataset_name,
        "feature_names": prepared.feature_names,
        "random_seed": seed,
        "training_config": if_cfg,
        "threshold": asdict(threshold),
        "train_rows": len(prepared.train_df),
        "val_rows": len(prepared.val_df),
        "test_rows": len(prepared.test_df),
        "train_anomaly_fraction": prepared.train_anomaly_fraction,
        "model_type": "sklearn.ensemble.IsolationForest",
        "temporal_context_method": "engineered lag/rolling/rate-of-change features, NOT a sequence model",
    }
    with open(os.path.join(out_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    return metadata


def load_trained(dataset_name: str) -> tuple[IsolationForest, object, dict]:
    cfg = load_config()
    out_dir = os.path.join(resolve_path(cfg["paths"]["models_dir"]), dataset_name)
    model = joblib.load(os.path.join(out_dir, "isolation_forest.joblib"))
    scaler = joblib.load(os.path.join(out_dir, "scaler.joblib"))
    with open(os.path.join(out_dir, "metadata.json")) as f:
        metadata = json.load(f)
    return model, scaler, metadata
