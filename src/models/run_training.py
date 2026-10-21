"""Stage 3 CLI: train and evaluate the Isolation Forest detector for every
labeled dataset (microsoft, kaggle). AWS/NAB series are unlabeled and are
scored descriptively elsewhere, not trained/evaluated with detection metrics.
"""
from __future__ import annotations

from src.models.anomaly_detector import train_and_save
from src.models.evaluate import evaluate_on_test, save_metrics
from src.preprocessing.adapters import load_kaggle, load_microsoft
from src.preprocessing.pipeline import prepare_dataset


def run_for(dataset_name: str, loader) -> None:
    loaded = loader()
    prepared = prepare_dataset(loaded)
    metadata = train_and_save(prepared, dataset_name)
    threshold = metadata["threshold"]["chosen_threshold"]

    from src.models.anomaly_detector import load_trained
    model, _scaler, _meta = load_trained(dataset_name)

    metrics = evaluate_on_test(prepared, model, threshold, dataset_name, loaded.timestamp_col)
    path = save_metrics(metrics)

    print(f"[{dataset_name}] threshold selection: {metadata['threshold']}")
    print(f"[{dataset_name}] test metrics written to {path}")
    print(
        f"[{dataset_name}] precision={metrics.precision:.3f} recall={metrics.recall:.3f} "
        f"f1={metrics.f1:.3f} fpr={metrics.false_positive_rate:.3f} "
        f"false_alarms_per_hour={metrics.false_alarms_per_hour} "
        f"roc_auc={metrics.roc_auc} pr_auc={metrics.pr_auc}"
    )


def main() -> None:
    run_for("microsoft", load_microsoft)
    run_for("kaggle", load_kaggle)


if __name__ == "__main__":
    main()
