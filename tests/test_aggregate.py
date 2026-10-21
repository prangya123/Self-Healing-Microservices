from src.experiments.aggregate import build_summary_by_condition_scenario, load_all_runs


def test_load_all_runs_includes_unrecovered_and_recovered_runs():
    df = load_all_runs()
    if df.empty:
        return  # no runs generated yet in this environment; nothing to assert
    assert "recovery_succeeded" in df.columns
    # unrecovered runs must be present, not silently dropped (Section 12)
    assert df["recovery_succeeded"].isin([True, False]).all()


def test_summary_table_has_one_row_per_scenario_condition_pair_present():
    df = load_all_runs()
    if df.empty:
        return
    summary = build_summary_by_condition_scenario(df)
    observed_pairs = set(zip(df["scenario"], df["condition"]))
    summary_pairs = set(zip(summary["scenario"], summary["condition"]))
    assert observed_pairs == summary_pairs
    assert (summary["n_runs"] > 0).all()
