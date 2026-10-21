"""Source-specific dataset adapters.

Each adapter loads its raw file(s) and returns a standardized, cleaned
DataFrame plus a CleaningReport, using only the columns actually observed
during Stage 1 inspection (see results/reports/dataset_inspection_report.md).
No cross-dataset concatenation happens here: each source keeps its own
feature space because they are not compatible (Section 3 of the brief).
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import pandas as pd

from src.common.config import load_config, resolve_path
from src.preprocessing.cleaning import CleaningReport, clean_timeseries


@dataclass
class LoadedDataset:
    name: str
    df: pd.DataFrame
    timestamp_col: str
    value_cols: list[str]
    label_col: str | None
    has_labels: bool
    report: CleaningReport


def load_microsoft() -> LoadedDataset:
    cfg = load_config()
    ds_cfg = cfg["datasets"]["microsoft"]
    path = resolve_path(cfg["paths"]["microsoft_csv"])
    raw = pd.read_csv(path)
    df, report = clean_timeseries(
        raw,
        timestamp_col=ds_cfg["timestamp_col"],
        value_cols=ds_cfg["value_cols"],
        label_col=ds_cfg["label_col"],
        source_name="microsoft",
        gap_multiplier=cfg["preprocessing"]["max_gap_multiplier_before_flag"],
    )
    return LoadedDataset(
        name="microsoft",
        df=df,
        timestamp_col=ds_cfg["timestamp_col"],
        value_cols=ds_cfg["value_cols"],
        label_col=ds_cfg["label_col"],
        has_labels=ds_cfg["has_labels"],
        report=report,
    )


def load_kaggle() -> LoadedDataset:
    cfg = load_config()
    ds_cfg = cfg["datasets"]["kaggle"]
    path = resolve_path(cfg["paths"]["kaggle_csv"])
    raw = pd.read_csv(path)
    df, report = clean_timeseries(
        raw,
        timestamp_col=ds_cfg["timestamp_col"],
        value_cols=ds_cfg["value_cols"],
        label_col=ds_cfg["label_col"],
        source_name="kaggle",
        gap_multiplier=cfg["preprocessing"]["max_gap_multiplier_before_flag"],
    )
    return LoadedDataset(
        name="kaggle",
        df=df,
        timestamp_col=ds_cfg["timestamp_col"],
        value_cols=ds_cfg["value_cols"],
        label_col=ds_cfg["label_col"],
        has_labels=ds_cfg["has_labels"],
        report=report,
    )


def load_aws_cloudwatch_all() -> dict[str, LoadedDataset]:
    """Each CSV is an independent series (different instance/time range) with
    no shared service identifier, so these are NOT merged into one dataframe.
    Confirmed unlabeled public benchmark data (see config.yaml note)."""
    cfg = load_config()
    ds_cfg = cfg["datasets"]["aws_cloudwatch"]
    directory = resolve_path(cfg["paths"]["aws_cloudwatch_dir"])
    paths = sorted(glob.glob(os.path.join(directory, "*.csv")))
    out: dict[str, LoadedDataset] = {}
    for path in paths:
        series_id = os.path.basename(path).rsplit(".", 1)[0]
        raw = pd.read_csv(path)
        df, report = clean_timeseries(
            raw,
            timestamp_col=ds_cfg["timestamp_col"],
            value_cols=ds_cfg["value_cols"],
            label_col=None,
            source_name=f"aws_cloudwatch:{series_id}",
            gap_multiplier=cfg["preprocessing"]["max_gap_multiplier_before_flag"],
        )
        out[series_id] = LoadedDataset(
            name=f"aws_cloudwatch:{series_id}",
            df=df,
            timestamp_col=ds_cfg["timestamp_col"],
            value_cols=ds_cfg["value_cols"],
            label_col=None,
            has_labels=False,
            report=report,
        )
    return out
