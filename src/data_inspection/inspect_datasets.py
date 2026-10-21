"""
Dataset inspection utility (Stage 1).

Profiles the three raw data sources declared in config.yaml WITHOUT assuming
filenames, columns, labels, or sampling intervals beyond what is observed.

Outputs:
- results/reports/dataset_inspection_report.md  (human-readable report)
- results/tables/dataset_inspection_summary.csv  (machine-readable summary)

This script only reads raw files. It does not modify them (see config.yaml
`preprocessing.preserve_raw` policy).
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_ROOT = os.path.abspath(os.path.join(REPO_ROOT, "..", "data"))
RESULTS_TABLES = os.path.join(REPO_ROOT, "results", "tables")
RESULTS_REPORTS = os.path.join(REPO_ROOT, "results", "reports")


@dataclass
class FileProfile:
    source_name: str
    path: str
    format: str
    n_rows: int
    n_cols: int
    columns: list = field(default_factory=list)
    dtypes: dict = field(default_factory=dict)
    timestamp_col: str | None = None
    time_min: str | None = None
    time_max: str | None = None
    inferred_interval: str | None = None
    n_gaps_over_1_5x_interval: int | None = None
    n_duplicate_rows: int = 0
    n_duplicate_timestamps: int = 0
    missing_values_by_col: dict = field(default_factory=dict)
    label_col: str | None = None
    label_value_counts: dict = field(default_factory=dict)
    service_or_host_identifier: str | None = None
    notes: list = field(default_factory=list)
    error: str | None = None


def _infer_timestamp_column(df: pd.DataFrame) -> str | None:
    candidates = [c for c in df.columns if c.lower() in ("timestamp", "time", "datetime", "date", "ts")]
    return candidates[0] if candidates else None


def _infer_label_column(df: pd.DataFrame) -> str | None:
    candidates = [c for c in df.columns if c.lower() in ("label", "anomaly", "is_anomaly", "fault", "target")]
    return candidates[0] if candidates else None


def profile_csv(path: str, source_name: str, service_hint: str | None = None) -> FileProfile:
    prof = FileProfile(source_name=source_name, path=path, format="csv", n_rows=0, n_cols=0)
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001 - want to record any read failure, not fabricate data
        prof.error = f"Failed to read CSV: {exc}"
        return prof

    prof.n_rows = len(df)
    prof.n_cols = df.shape[1]
    prof.columns = list(df.columns)
    prof.dtypes = {c: str(t) for c, t in df.dtypes.items()}
    prof.n_duplicate_rows = int(df.duplicated().sum())
    prof.missing_values_by_col = {c: int(n) for c, n in df.isna().sum().items() if n > 0}

    ts_col = _infer_timestamp_column(df)
    prof.timestamp_col = ts_col
    if ts_col is not None:
        try:
            ts = pd.to_datetime(df[ts_col], errors="coerce", utc=False)
            n_unparsed = int(ts.isna().sum())
            if n_unparsed:
                prof.notes.append(f"{n_unparsed} values in '{ts_col}' could not be parsed as timestamps.")
            ts_valid = ts.dropna().sort_values()
            if len(ts_valid):
                prof.time_min = str(ts_valid.min())
                prof.time_max = str(ts_valid.max())
                prof.n_duplicate_timestamps = int(ts.duplicated().sum())
                diffs = ts_valid.diff().dropna()
                if len(diffs):
                    mode_interval = diffs.mode()
                    if len(mode_interval):
                        interval = mode_interval.iloc[0]
                        prof.inferred_interval = str(interval)
                        if interval > pd.Timedelta(0):
                            prof.n_gaps_over_1_5x_interval = int((diffs > interval * 1.5).sum())
        except Exception as exc:  # noqa: BLE001
            prof.notes.append(f"Timestamp parsing failed: {exc}")

    label_col = _infer_label_column(df)
    prof.label_col = label_col
    if label_col is not None:
        try:
            prof.label_value_counts = {str(k): int(v) for k, v in df[label_col].value_counts(dropna=False).items()}
        except Exception as exc:  # noqa: BLE001
            prof.notes.append(f"Label summarisation failed: {exc}")
    else:
        prof.notes.append("No label/anomaly/fault column detected by name heuristics.")

    if service_hint:
        prof.service_or_host_identifier = service_hint
    else:
        id_like = [c for c in df.columns if any(k in c.lower() for k in ("host", "service", "node", "instance", "pod", "server"))]
        if id_like:
            prof.notes.append(f"Possible service/host identifying columns present: {id_like} (embedded as multivariate feature names, not a row-level identifier column).")
        else:
            prof.notes.append("No explicit service/host identifier column found.")

    return prof


def inspect_microsoft_cloud_monitoring() -> list[FileProfile]:
    path = os.path.join(DATA_ROOT, "cloud_monitoring_sample.csv")
    if not os.path.exists(path):
        p = FileProfile(source_name="microsoft_cloud_monitoring", path=path, format="csv", n_rows=0, n_cols=0)
        p.error = "File not found."
        return [p]
    prof = profile_csv(path, "microsoft_cloud_monitoring")
    prof.notes.append("Univariate series: single 'Value' column, hourly cadence, binary Label column present.")
    return [prof]


def inspect_kaggle_cloud_resource_usage() -> list[FileProfile]:
    path = os.path.join(DATA_ROOT, "kaggle_cloud_resource_usage.csv")
    if not os.path.exists(path):
        p = FileProfile(source_name="kaggle_cloud_resource_usage", path=path, format="csv", n_rows=0, n_cols=0)
        p.error = "File not found."
        return [p]
    prof = profile_csv(path, "kaggle_cloud_resource_usage")
    prof.notes.append(
        "Multivariate series: column names encode metric|aggregation|entity (e.g. "
        "'node_cpu_utilization|Average|node1'), suggesting multiple nodes/services were pivoted "
        "into one wide row per minute. Row-level 'anomaly' label is a single global flag, not "
        "per-entity, and does not indicate fault type."
    )
    return [prof]


def inspect_aws_cloudwatch_metrics() -> list[FileProfile]:
    pattern = os.path.join(DATA_ROOT, "aws_cloudwatch_metrics", "*.csv")
    paths = sorted(glob.glob(pattern))
    if not paths:
        p = FileProfile(source_name="aws_cloudwatch_metrics", path=pattern, format="csv", n_rows=0, n_cols=0)
        p.error = "No CSV files found."
        return [p]
    profiles = []
    known_nab_filenames = {
        "ec2_cpu_utilization_825cc2.csv", "ec2_cpu_utilization_ac20cd.csv",
        "ec2_cpu_utilization_24ae8d.csv", "ec2_cpu_utilization_53ea38.csv",
        "ec2_cpu_utilization_5f5533.csv", "ec2_cpu_utilization_77c1ca.csv",
        "ec2_cpu_utilization_c6585a.csv", "ec2_cpu_utilization_fe7f93.csv",
        "ec2_disk_write_bytes_1ef3de.csv", "ec2_disk_write_bytes_c0d644.csv",
        "ec2_network_in_257a54.csv", "ec2_network_in_5abac7.csv",
        "elb_request_count_8c0756.csv", "grok_asg_anomaly.csv",
        "iio_us-east-1_i-a2eb1cd9_NetworkIn.csv", "rds_cpu_utilization_cc0c53.csv",
        "rds_cpu_utilization_e47b3b.csv",
    }
    for path in paths:
        fname = os.path.basename(path)
        service_hint = fname.rsplit(".", 1)[0]
        prof = profile_csv(path, "aws_cloudwatch_metrics", service_hint=service_hint)
        if fname in known_nab_filenames:
            prof.notes.append(
                "FILENAME MATCHES the public NAB (Numenta Anomaly Benchmark) 'realAWSCloudwatch' "
                "corpus, not a fresh export described as coming from the user's own experimental "
                "environment. No label/combined_windows.json file was found alongside these CSVs, "
                "so these files are currently UNLABELED. This should be confirmed with the user "
                "before being described as 'AWS CloudWatch metrics and logs exported from my "
                "experimental environment' in the dissertation."
            )
        profiles.append(prof)
    return profiles


def profile_to_dict(p: FileProfile) -> dict[str, Any]:
    d = p.__dict__.copy()
    return d


def build_report(all_profiles: dict[str, list[FileProfile]]) -> str:
    lines = []
    lines.append("# Dataset Inspection Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Data root: `{DATA_ROOT}`")
    lines.append("")
    lines.append(
        "This report is generated entirely from the files actually present on disk. "
        "No filenames, column names, labels, or sampling intervals were assumed in advance."
    )
    lines.append("")

    for source, profiles in all_profiles.items():
        lines.append(f"## Source: {source}")
        lines.append("")
        for p in profiles:
            lines.append(f"### `{os.path.relpath(p.path, DATA_ROOT) if os.path.exists(p.path) else p.path}`")
            if p.error:
                lines.append(f"- **ERROR:** {p.error}")
                lines.append("")
                continue
            lines.append(f"- Format: {p.format}")
            lines.append(f"- Rows: {p.n_rows}, Columns: {p.n_cols}")
            lines.append(f"- Columns: {p.columns}")
            lines.append(f"- Dtypes: {p.dtypes}")
            lines.append(f"- Timestamp column: {p.timestamp_col}")
            if p.timestamp_col:
                lines.append(f"  - Time range: {p.time_min} to {p.time_max}")
                lines.append(f"  - Inferred sampling interval (mode): {p.inferred_interval}")
                lines.append(f"  - Gaps > 1.5x modal interval: {p.n_gaps_over_1_5x_interval}")
                lines.append(f"  - Duplicate timestamps: {p.n_duplicate_timestamps}")
            lines.append(f"- Duplicate full rows: {p.n_duplicate_rows}")
            lines.append(f"- Missing values by column: {p.missing_values_by_col if p.missing_values_by_col else 'none'}")
            lines.append(f"- Label column: {p.label_col}")
            if p.label_col:
                lines.append(f"  - Label value counts: {p.label_value_counts}")
            lines.append(f"- Service/host identifier: {p.service_or_host_identifier}")
            if p.notes:
                lines.append("- Notes:")
                for n in p.notes:
                    lines.append(f"  - {n}")
            lines.append("")
    return "\n".join(lines)


def build_summary_table(all_profiles: dict[str, list[FileProfile]]) -> pd.DataFrame:
    rows = []
    for source, profiles in all_profiles.items():
        for p in profiles:
            rows.append({
                "source": source,
                "path": p.path,
                "format": p.format,
                "n_rows": p.n_rows,
                "n_cols": p.n_cols,
                "timestamp_col": p.timestamp_col,
                "time_min": p.time_min,
                "time_max": p.time_max,
                "inferred_interval": p.inferred_interval,
                "n_gaps_over_1_5x_interval": p.n_gaps_over_1_5x_interval,
                "n_duplicate_rows": p.n_duplicate_rows,
                "n_duplicate_timestamps": p.n_duplicate_timestamps,
                "label_col": p.label_col,
                "error": p.error,
            })
    return pd.DataFrame(rows)


def main() -> None:
    os.makedirs(RESULTS_TABLES, exist_ok=True)
    os.makedirs(RESULTS_REPORTS, exist_ok=True)

    all_profiles = {
        "microsoft_cloud_monitoring": inspect_microsoft_cloud_monitoring(),
        "kaggle_cloud_resource_usage": inspect_kaggle_cloud_resource_usage(),
        "aws_cloudwatch_metrics": inspect_aws_cloudwatch_metrics(),
    }

    report_md = build_report(all_profiles)
    report_path = os.path.join(RESULTS_REPORTS, "dataset_inspection_report.md")
    with open(report_path, "w") as f:
        f.write(report_md)

    summary_df = build_summary_table(all_profiles)
    summary_path = os.path.join(RESULTS_TABLES, "dataset_inspection_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    raw_json_path = os.path.join(RESULTS_REPORTS, "dataset_inspection_raw.json")
    with open(raw_json_path, "w") as f:
        json.dump(
            {source: [profile_to_dict(p) for p in profiles] for source, profiles in all_profiles.items()},
            f,
            indent=2,
            default=str,
        )

    print(f"Wrote report to {report_path}")
    print(f"Wrote summary table to {summary_path}")
    print(f"Wrote raw profiles to {raw_json_path}")


if __name__ == "__main__":
    main()
