"""End-to-end, leakage-safe preprocessing pipeline for a single dataset.

Stages: load+clean (adapters.py) -> causal feature engineering (features.py)
-> drop incomplete leading rows -> chronological split (splits.py) ->
fit scaler on TRAIN ONLY -> transform val/test with the frozen scaler.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.common.config import load_config, resolve_path
from src.preprocessing.adapters import LoadedDataset
from src.preprocessing.features import add_temporal_features, drop_rows_with_incomplete_features
from src.preprocessing.splits import SplitResult, chronological_split


@dataclass
class PreparedDataset:
    name: str
    feature_names: list[str]
    scaler: StandardScaler
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    X_train: np.ndarray
    X_val: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray | None
    y_val: np.ndarray | None
    y_test: np.ndarray | None
    has_labels: bool
    n_rows_dropped_incomplete_features: int
    n_rows_dropped_boundary_guard: int
    train_anomaly_fraction: float | None


def prepare_dataset(loaded: LoadedDataset) -> PreparedDataset:
    cfg = load_config()
    pp_cfg = cfg["preprocessing"]

    n_before_features = len(loaded.df)

    df_feat, new_feature_cols = add_temporal_features(
        loaded.df,
        value_cols=loaded.value_cols,
        lags=pp_cfg["lags"],
        rolling_windows=pp_cfg["rolling_windows"],
    )
    df_feat = drop_rows_with_incomplete_features(df_feat, new_feature_cols)
    n_dropped_incomplete = n_before_features - len(df_feat)

    all_feature_cols = loaded.value_cols + new_feature_cols

    split: SplitResult = chronological_split(
        df_feat,
        train_frac=pp_cfg["splits"]["train_frac"],
        val_frac=pp_cfg["splits"]["val_frac"],
        test_frac=pp_cfg["splits"]["test_frac"],
        boundary_guard_steps=pp_cfg["splits"]["boundary_guard_steps"],
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(split.train[all_feature_cols].values)
    X_val = scaler.transform(split.val[all_feature_cols].values) if len(split.val) else np.empty((0, len(all_feature_cols)))
    X_test = scaler.transform(split.test[all_feature_cols].values) if len(split.test) else np.empty((0, len(all_feature_cols)))

    y_train = y_val = y_test = None
    train_anomaly_fraction = None
    if loaded.has_labels and loaded.label_col:
        y_train = split.train[loaded.label_col].values
        y_val = split.val[loaded.label_col].values if len(split.val) else np.array([])
        y_test = split.test[loaded.label_col].values if len(split.test) else np.array([])
        train_anomaly_fraction = float(np.mean(y_train)) if len(y_train) else None

    return PreparedDataset(
        name=loaded.name,
        feature_names=all_feature_cols,
        scaler=scaler,
        train_df=split.train,
        val_df=split.val,
        test_df=split.test,
        X_train=X_train,
        X_val=X_val,
        X_test=X_test,
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
        has_labels=loaded.has_labels,
        n_rows_dropped_incomplete_features=n_dropped_incomplete,
        n_rows_dropped_boundary_guard=split.n_dropped_for_boundary_guard,
        train_anomaly_fraction=train_anomaly_fraction,
    )


def write_preprocessing_report(loaded: LoadedDataset, prepared: PreparedDataset) -> str:
    cfg = load_config()
    reports_dir = resolve_path(cfg["paths"]["results_reports"])
    os.makedirs(reports_dir, exist_ok=True)
    safe_name = loaded.name.replace(":", "_")
    path = os.path.join(reports_dir, f"preprocessing_report_{safe_name}.md")

    lines = [f"# Preprocessing Report: {loaded.name}", ""]
    r = loaded.report
    lines += [
        f"- Rows in (post raw-read): {r.n_rows_in}",
        f"- Rows after cleaning: {r.n_rows_out}",
        f"- Exact duplicate rows dropped: {r.n_exact_duplicates_dropped}",
        f"- Duplicate timestamps remaining after dedup: {r.n_duplicate_timestamps_remaining}",
        f"- Rows dropped for unparseable timestamp: {r.n_rows_unparseable_timestamp_dropped}",
        f"- Inferred sampling interval: {r.inferred_interval}",
        f"- Gaps exceeding {cfg['preprocessing']['max_gap_multiplier_before_flag']}x modal interval: {r.n_gaps_over_threshold} (NOT interpolated)",
        f"- Missing values by column (pre feature engineering): {r.missing_values_by_col or 'none'}",
        f"- Time range: {r.time_min} to {r.time_max}",
        "",
        f"- Rows dropped due to incomplete lag/rolling features (leading rows): {prepared.n_rows_dropped_incomplete_features}",
        f"- Rows dropped at split boundaries to prevent window leakage: {prepared.n_rows_dropped_boundary_guard}",
        f"- Feature count: {len(prepared.feature_names)}",
        f"- Split sizes: train={len(prepared.train_df)}, val={len(prepared.val_df)}, test={len(prepared.test_df)}",
        f"- Has labels: {prepared.has_labels}",
    ]
    if prepared.has_labels:
        lines.append(
            f"- Training-split anomaly fraction: {prepared.train_anomaly_fraction:.4f}"
            if prepared.train_anomaly_fraction is not None else "- Training-split anomaly fraction: n/a"
        )
        if prepared.train_anomaly_fraction and prepared.train_anomaly_fraction > 0:
            lines.append(
                "  - NOTE: training split is NOT anomaly-free. The detector is trained on data "
                "that may contain anomalies; this is disclosed rather than assumed away."
            )
    lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
