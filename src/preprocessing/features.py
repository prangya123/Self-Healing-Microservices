"""Causal temporal feature engineering.

Every feature here uses only the current observation and strictly past
observations. There are no centered windows and no use of future rows,
per Section 7 of the project brief.
"""
from __future__ import annotations

import pandas as pd


def add_temporal_features(
    df: pd.DataFrame,
    value_cols: list[str],
    lags: list[int],
    rolling_windows: list[int],
) -> tuple[pd.DataFrame, list[str]]:
    """Adds, for each value column: current value (already present), lagged
    values, trailing rolling mean/std, and rate of change. Returns the
    augmented dataframe and the list of newly created feature column names.

    Assumes `df` is already sorted ascending by timestamp (see cleaning.py).
    Pandas `.rolling(window=w)` is right-aligned by default, i.e. the window
    for row t is [t-w+1, t] -- causal, never centered.
    """
    df = df.copy()
    new_cols: list[str] = []

    for col in value_cols:
        for lag in lags:
            name = f"{col}__lag{lag}"
            df[name] = df[col].shift(lag)
            new_cols.append(name)

        for window in rolling_windows:
            mean_name = f"{col}__roll_mean{window}"
            std_name = f"{col}__roll_std{window}"
            df[mean_name] = df[col].rolling(window=window, min_periods=window).mean()
            df[std_name] = df[col].rolling(window=window, min_periods=window).std()
            new_cols.extend([mean_name, std_name])

        rate_name = f"{col}__rate_of_change"
        df[rate_name] = df[col].diff()
        new_cols.append(rate_name)

    return df, new_cols


def drop_rows_with_incomplete_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Drops leading rows where lag/rolling features are NaN because there is
    not yet enough history (e.g. the first `max(lags, windows)` rows)."""
    return df.dropna(subset=feature_cols).reset_index(drop=True)
