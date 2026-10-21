import os

from src.data_inspection.inspect_datasets import (
    DATA_ROOT,
    inspect_aws_cloudwatch_metrics,
    inspect_kaggle_cloud_resource_usage,
    inspect_microsoft_cloud_monitoring,
)


def test_data_root_resolves_to_sibling_data_dir():
    assert os.path.basename(DATA_ROOT) == "data"
    assert os.path.isdir(DATA_ROOT)


def test_microsoft_profile_detects_label_and_hourly_cadence():
    profiles = inspect_microsoft_cloud_monitoring()
    assert len(profiles) == 1
    p = profiles[0]
    assert p.error is None
    assert p.label_col is not None
    assert p.n_rows > 0
    assert p.inferred_interval == "0 days 01:00:00"


def test_kaggle_profile_detects_anomaly_label_and_minute_cadence():
    profiles = inspect_kaggle_cloud_resource_usage()
    assert len(profiles) == 1
    p = profiles[0]
    assert p.error is None
    assert p.label_col == "anomaly"
    assert p.inferred_interval == "0 days 00:01:00"
    assert p.n_duplicate_rows == 0


def test_aws_cloudwatch_profiles_flag_nab_origin_and_missing_labels():
    profiles = inspect_aws_cloudwatch_metrics()
    assert len(profiles) >= 1
    for p in profiles:
        assert p.error is None
        assert p.label_col is None
    flagged = [p for p in profiles if any("NAB" in n for n in p.notes)]
    assert len(flagged) > 0, "Expected at least one file to be flagged as matching the public NAB corpus"
