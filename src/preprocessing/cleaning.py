"""Generic, source-agnostic time series cleaning.

Rules enforced here (see Section 7 of the project brief):
- Raw files are never modified; cleaning always happens on an in-memory copy.
- Timestamps are parsed and standardized to UTC.
- Records are sorted within the series.
- Exact duplicate rows are dropped explicitly (reported, not silently removed).
- Missingness and sampling gaps are reported, never silently interpolated.
- No resampling unless a caller explicitly opts in with a documented reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CleaningReport:
    source_name: str
    n_rows_in: int
    n_rows_out: int
    n_exact_duplicates_dropped: int
    n_duplicate_timestamps_remaining: int
    n_rows_unparseable_timestamp_dropped: int
    inferred_interval: str | None
    n_gaps_over_threshold: int
    missing_values_by_col: dict = field(default_factory=dict)
    time_min: str | None = None
    time_max: str | None = None


def clean_timeseries(
    df: pd.DataFrame,
    timestamp_col: str,
    value_cols: list[str],
    source_name: str,
    label_col: str | None = None,
    timezone: str = "UTC",
    gap_multiplier: float = 1.5,
) -> tuple[pd.DataFrame, CleaningReport]:
    df = df.copy()
    n_in = len(df)

    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce", utc=True)
    n_unparseable = int(df[timestamp_col].isna().sum())
    df = df.dropna(subset=[timestamp_col])

    keep_cols = [timestamp_col] + value_cols + ([label_col] if label_col else [])
    df = df[keep_cols]

    missing = {c: int(n) for c, n in df.isna().sum().items() if n > 0}

    n_exact_dupes = int(df.duplicated().sum())
    df = df.drop_duplicates(keep="first")

    df = df.sort_values(timestamp_col).reset_index(drop=True)

    n_dup_ts_remaining = int(df[timestamp_col].duplicated().sum())

    inferred_interval = None
    n_gaps = 0
    if len(df) > 1:
        diffs = df[timestamp_col].diff().dropna()
        mode_interval = diffs.mode()
        if len(mode_interval):
            interval = mode_interval.iloc[0]
            inferred_interval = str(interval)
            if interval > pd.Timedelta(0):
                n_gaps = int((diffs > interval * gap_multiplier).sum())

    report = CleaningReport(
        source_name=source_name,
        n_rows_in=n_in,
        n_rows_out=len(df),
        n_exact_duplicates_dropped=n_exact_dupes,
        n_duplicate_timestamps_remaining=n_dup_ts_remaining,
        n_rows_unparseable_timestamp_dropped=n_unparseable,
        inferred_interval=inferred_interval,
        n_gaps_over_threshold=n_gaps,
        missing_values_by_col=missing,
        time_min=str(df[timestamp_col].min()) if len(df) else None,
        time_max=str(df[timestamp_col].max()) if len(df) else None,
    )
    return df, report
