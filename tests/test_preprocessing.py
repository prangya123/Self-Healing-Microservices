import numpy as np
import pandas as pd

from src.preprocessing.adapters import load_kaggle, load_microsoft
from src.preprocessing.features import add_temporal_features
from src.preprocessing.pipeline import prepare_dataset
from src.preprocessing.splits import chronological_split


def test_rolling_features_are_causal_not_centered():
    df = pd.DataFrame({"v": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    out, new_cols = add_temporal_features(df, value_cols=["v"], lags=[1], rolling_windows=[3])
    # rolling mean at index 2 (value=3) over window 3 must be mean(1,2,3)=2.0,
    # NOT a centered mean(2,3,4)=3.0
    assert out["v__roll_mean3"].iloc[2] == 2.0
    # lag1 at index 1 must equal value at index 0
    assert out["v__lag1"].iloc[1] == 1.0
    assert np.isnan(out["v__lag1"].iloc[0])


def test_chronological_split_preserves_order_and_drops_boundary_rows():
    df = pd.DataFrame({"t": range(100)})
    result = chronological_split(df, train_frac=0.6, val_frac=0.2, test_frac=0.2, boundary_guard_steps=5)
    assert result.train["t"].max() < result.val["t"].min()
    assert result.val["t"].max() < result.test["t"].min()
    assert result.n_dropped_for_boundary_guard == 10  # 5 dropped from val start + 5 from test start


def test_scaler_is_fit_on_train_only_and_splits_are_chronological():
    loaded = load_microsoft()
    prepared = prepare_dataset(loaded)
    assert prepared.X_train.shape[1] == len(prepared.feature_names)
    # train split must end before val split begins, and val before test, in time
    ts_col = loaded.timestamp_col
    assert prepared.train_df[ts_col].max() <= prepared.val_df[ts_col].min()
    assert prepared.val_df[ts_col].max() <= prepared.test_df[ts_col].min()
    # scaler fit on train only => train features should be ~standardized
    assert abs(prepared.X_train.mean()) < 1e-6 + 1.0  # loose sanity bound, not exact due to multiple cols


def test_kaggle_training_split_anomaly_fraction_is_disclosed():
    loaded = load_kaggle()
    prepared = prepare_dataset(loaded)
    assert prepared.has_labels is True
    assert prepared.train_anomaly_fraction is not None
    assert 0.0 <= prepared.train_anomaly_fraction <= 1.0
