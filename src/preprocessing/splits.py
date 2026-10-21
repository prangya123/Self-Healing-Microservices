"""Chronological train/validation/test splitting with boundary leakage guards.

Splits are strictly time-ordered (no shuffling). Rows adjacent to a split
boundary are dropped so that lag/rolling-window features in the validation
or test set cannot have been computed using rows now assigned to a
different split.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SplitResult:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    n_dropped_for_boundary_guard: int


def chronological_split(
    df: pd.DataFrame,
    train_frac: float,
    val_frac: float,
    test_frac: float,
    boundary_guard_steps: int,
) -> SplitResult:
    assert abs(train_frac + val_frac + test_frac - 1.0) < 1e-6, "fractions must sum to 1.0"
    n = len(df)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train = df.iloc[:train_end]
    val_full = df.iloc[train_end:val_end]
    test_full = df.iloc[val_end:]

    g = boundary_guard_steps
    val = val_full.iloc[g:] if len(val_full) > g else val_full.iloc[0:0]
    test = test_full.iloc[g:] if len(test_full) > g else test_full.iloc[0:0]

    n_dropped = (len(val_full) - len(val)) + (len(test_full) - len(test))

    return SplitResult(
        train=train.reset_index(drop=True),
        val=val.reset_index(drop=True),
        test=test.reset_index(drop=True),
        n_dropped_for_boundary_guard=n_dropped,
    )
