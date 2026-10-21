import os

from src.common.config import load_config, resolve_path
from src.models.anomaly_detector import load_trained, select_threshold, train_and_save
from src.models.evaluate import evaluate_on_test
from src.preprocessing.adapters import load_microsoft
from src.preprocessing.pipeline import prepare_dataset


def test_threshold_is_selected_on_validation_only():
    loaded = load_microsoft()
    prepared = prepare_dataset(loaded)
    metadata = train_and_save(prepared, "microsoft")
    assert metadata["threshold"]["val_has_labels"] is True
    assert metadata["threshold"]["chosen_val_f1"] is not None
    assert 0.0 <= metadata["threshold"]["chosen_val_f1"] <= 1.0


def test_trained_artifacts_are_persisted_and_reloadable():
    loaded = load_microsoft()
    prepared = prepare_dataset(loaded)
    train_and_save(prepared, "microsoft")
    cfg = load_config()
    out_dir = os.path.join(resolve_path(cfg["paths"]["models_dir"]), "microsoft")
    assert os.path.exists(os.path.join(out_dir, "isolation_forest.joblib"))
    assert os.path.exists(os.path.join(out_dir, "scaler.joblib"))
    assert os.path.exists(os.path.join(out_dir, "metadata.json"))

    model, scaler, metadata = load_trained("microsoft")
    assert metadata["model_type"] == "sklearn.ensemble.IsolationForest"
    assert metadata["feature_names"] == prepared.feature_names


def test_test_metrics_applied_once_with_frozen_threshold():
    loaded = load_microsoft()
    prepared = prepare_dataset(loaded)
    metadata = train_and_save(prepared, "microsoft")
    model, _scaler, _meta = load_trained("microsoft")
    threshold = metadata["threshold"]["chosen_threshold"]

    metrics = evaluate_on_test(prepared, model, threshold, "microsoft", loaded.timestamp_col)
    assert metrics.threshold == threshold
    assert len(metrics.confusion_matrix) == 2 and len(metrics.confusion_matrix[0]) == 2
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1 <= 1.0
    assert metrics.roc_auc is not None and 0.0 <= metrics.roc_auc <= 1.0
