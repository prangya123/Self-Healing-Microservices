"""Test-set evaluation for a trained anomaly detector.

Threshold is already frozen (selected on validation data only, see
anomaly_detector.select_threshold). This module only applies it once to the
held-out test split, exactly as required by Section 8.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

from src.common.config import load_config, resolve_path
from src.models.anomaly_detector import anomaly_score
from src.preprocessing.pipeline import PreparedDataset


@dataclass
class DetectionMetrics:
    dataset_name: str
    n_test_rows: int
    threshold: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    false_alarms_per_hour: float | None
    roc_auc: float | None
    pr_auc: float | None
    confusion_matrix: list  # [[tn, fp], [fn, tp]]
    notes: list


def evaluate_on_test(
    prepared: PreparedDataset,
    model,
    threshold: float,
    dataset_name: str,
    timestamp_col: str,
    save_raw_scores: bool = True,
) -> DetectionMetrics:
    notes = []
    if not prepared.has_labels or prepared.y_test is None or len(prepared.y_test) == 0:
        notes.append("No test labels available: detection metrics cannot be computed for this dataset.")
        return DetectionMetrics(
            dataset_name=dataset_name, n_test_rows=len(prepared.test_df), threshold=threshold,
            precision=float("nan"), recall=float("nan"), f1=float("nan"),
            false_positive_rate=float("nan"), false_alarms_per_hour=None,
            roc_auc=None, pr_auc=None, confusion_matrix=[], notes=notes,
        )

    scores = anomaly_score(model, prepared.X_test)
    y_true = prepared.y_test
    y_pred = (scores > threshold).astype(int)

    if save_raw_scores:
        cfg = load_config()
        tables_dir = resolve_path(cfg["paths"]["results_tables"])
        os.makedirs(tables_dir, exist_ok=True)
        raw_path = os.path.join(tables_dir, f"detection_scores_{dataset_name}.csv")
        pd.DataFrame({"y_true": y_true, "anomaly_score": scores}).to_csv(raw_path, index=False)

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else float("nan")

    false_alarms_per_hour = None
    if timestamp_col in prepared.test_df.columns and len(prepared.test_df) > 1:
        span = prepared.test_df[timestamp_col].max() - prepared.test_df[timestamp_col].min()
        hours = span.total_seconds() / 3600.0
        if hours > 0:
            false_alarms_per_hour = float(fp / hours)

    roc_auc = None
    pr_auc = None
    if len(np.unique(y_true)) > 1:
        roc_auc = float(roc_auc_score(y_true, scores))
        pr_auc = float(average_precision_score(y_true, scores))
    else:
        notes.append("Test split has only one class present: ROC-AUC/PR-AUC not computed.")

    return DetectionMetrics(
        dataset_name=dataset_name,
        n_test_rows=len(prepared.test_df),
        threshold=float(threshold),
        precision=float(precision_score(y_true, y_pred, zero_division=0)),
        recall=float(recall_score(y_true, y_pred, zero_division=0)),
        f1=float(f1_score(y_true, y_pred, zero_division=0)),
        false_positive_rate=float(fpr),
        false_alarms_per_hour=false_alarms_per_hour,
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        confusion_matrix=cm.tolist(),
        notes=notes,
    )


def save_metrics(metrics: DetectionMetrics) -> str:
    cfg = load_config()
    tables_dir = resolve_path(cfg["paths"]["results_tables"])
    os.makedirs(tables_dir, exist_ok=True)
    path = os.path.join(tables_dir, f"detection_metrics_{metrics.dataset_name}.json")
    with open(path, "w") as f:
        json.dump(asdict(metrics), f, indent=2, default=str)
    return path
