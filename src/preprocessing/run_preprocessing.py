"""Stage 2 CLI: run the leakage-safe preprocessing pipeline for every labeled
dataset and write preprocessing reports. AWS/NAB series are profiled per-file
on demand during Stage 3 (unsupervised, descriptive use only) since they have
no labels and are not pooled into one combined dataset.
"""
from __future__ import annotations

from src.preprocessing.adapters import load_kaggle, load_microsoft
from src.preprocessing.pipeline import prepare_dataset, write_preprocessing_report


def main() -> None:
    for loader in (load_microsoft, load_kaggle):
        loaded = loader()
        prepared = prepare_dataset(loaded)
        path = write_preprocessing_report(loaded, prepared)
        print(f"[{loaded.name}] report written to {path}")
        print(
            f"[{loaded.name}] train={len(prepared.train_df)} val={len(prepared.val_df)} "
            f"test={len(prepared.test_df)} features={len(prepared.feature_names)}"
        )


if __name__ == "__main__":
    main()
