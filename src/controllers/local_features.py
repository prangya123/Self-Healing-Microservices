"""Causal feature engineering for LIVE application telemetry.

Same methodology as src/preprocessing/features.py (current value, lag,
rolling mean/std, rate of change -- all strictly backward-looking) but
applied to the local app's own telemetry schema, which is NOT the same
feature space as the Microsoft/Kaggle/AWS datasets. A separate model is
trained for this source rather than reusing those models, per Section 3/8.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.app.telemetry import TelemetryRecord

BASE_COLUMNS = ["mem_mb", "cpu_percent", "work_latency_ms", "work_success"]


def _records_to_frame(history: list[TelemetryRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "mem_mb": [r.mem_mb if r.mem_mb is not None else np.nan for r in history],
            "cpu_percent": [r.cpu_percent if r.cpu_percent is not None else np.nan for r in history],
            "work_latency_ms": [r.work_latency_ms if r.work_latency_ms is not None else np.nan for r in history],
            "work_success": [1.0 if r.work_success else 0.0 for r in history],
        }
    )


def build_feature_frame(history: list[TelemetryRecord], lookback_window: int) -> tuple[pd.DataFrame, list[str]]:
    df = _records_to_frame(history)
    feature_cols: list[str] = []

    for col in ["mem_mb", "cpu_percent", "work_latency_ms"]:
        lag_name = f"{col}__lag1"
        roll_name = f"{col}__roll_mean{lookback_window}"
        rate_name = f"{col}__rate_of_change"
        df[lag_name] = df[col].shift(1)
        df[roll_name] = df[col].rolling(window=lookback_window, min_periods=lookback_window).mean()
        df[rate_name] = df[col].diff()
        feature_cols.extend([col, lag_name, roll_name, rate_name])

    success_roll_name = f"work_success__roll_mean{lookback_window}"
    df[success_roll_name] = df["work_success"].rolling(window=lookback_window, min_periods=lookback_window).mean()
    feature_cols.append(success_roll_name)

    return df, feature_cols


def latest_feature_vector(history: list[TelemetryRecord], lookback_window: int, feature_cols: list[str]) -> np.ndarray | None:
    """Returns the feature vector for the most recent record, or None if
    there isn't yet enough history (insufficient warmup)."""
    df, _ = build_feature_frame(history, lookback_window)
    row = df.iloc[-1]
    if row[feature_cols].isna().any():
        return None
    return row[feature_cols].values.astype(float).reshape(1, -1)
