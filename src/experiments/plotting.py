"""Stage 6: figures. Every figure is labeled with its data source and
evaluation mode so offline dataset evaluation, replay, and controlled local
experiments are never visually conflated (Section 6/13).

Condition colors are fixed per Section 13: baseline=orange, rule_based=blue,
ai_driven=green.
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

from src.common.config import load_config, resolve_path

CONDITION_COLORS = {
    "baseline": "#E69F00",
    "rule_based": "#0072B2",
    "ai_driven": "#009E73",
}
CONDITION_LABELS = {"baseline": "Baseline", "rule_based": "Rule-based", "ai_driven": "AI-driven"}
SCENARIO_LABELS = {
    "container_crash": "Container crash",
    "memory_leak": "Memory leak",
    "dependency_timeout": "Dependency timeout",
}


def _figures_dir() -> str:
    cfg = load_config()
    d = resolve_path(cfg["paths"]["results_figures"])
    os.makedirs(d, exist_ok=True)
    return d


def _tables_dir() -> str:
    cfg = load_config()
    return resolve_path(cfg["paths"]["results_tables"])


def _source_caption(ax, text: str) -> None:
    ax.annotate(text, xy=(0, -0.18), xycoords="axes fraction", fontsize=8, color="#555555")


# ---------------------------------------------------------------------------
# Offline dataset evaluation figures (Section 6A)
# ---------------------------------------------------------------------------

def plot_detection_metric_comparison() -> str | None:
    rows = []
    for name in ("microsoft", "kaggle"):
        path = os.path.join(_tables_dir(), f"detection_metrics_{name}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            m = json.load(f)
        if not np.isnan(m["precision"]):
            rows.append({"dataset": name, "precision": m["precision"], "recall": m["recall"], "f1": m["f1"]})
    if not rows:
        return None
    df = pd.DataFrame(rows).set_index("dataset")

    fig, ax = plt.subplots(figsize=(6, 4))
    df.plot(kind="bar", ax=ax, color=["#56B4E9", "#D55E00", "#009E73"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("Isolation Forest detection metrics (test split, offline dataset evaluation)")
    _source_caption(ax, "Source: results/tables/detection_metrics_*.json | Mode: offline dataset evaluation (Stage 3)")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "detection_metric_comparison.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_confusion_matrices() -> str | None:
    datasets = []
    for name in ("microsoft", "kaggle"):
        path = os.path.join(_tables_dir(), f"detection_metrics_{name}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            m = json.load(f)
        if m["confusion_matrix"]:
            datasets.append((name, np.array(m["confusion_matrix"])))
    if not datasets:
        return None

    fig, axes = plt.subplots(1, len(datasets), figsize=(5 * len(datasets), 4))
    if len(datasets) == 1:
        axes = [axes]
    for ax, (name, cm) in zip(axes, datasets):
        im = ax.imshow(cm, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["pred normal", "pred anomaly"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["true normal", "true anomaly"])
        ax.set_title(f"{name} (test split)")
        fig.colorbar(im, ax=ax, fraction=0.046)
    _source_caption(axes[0], "Source: results/tables/detection_metrics_*.json | Mode: offline dataset evaluation (Stage 3)")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "confusion_matrices.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_roc_pr_curves() -> str | None:
    datasets = []
    for name in ("microsoft", "kaggle"):
        path = os.path.join(_tables_dir(), f"detection_scores_{name}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        if df["y_true"].nunique() > 1:
            datasets.append((name, df))
    if not datasets:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for name, df in datasets:
        fpr, tpr, _ = roc_curve(df["y_true"], df["anomaly_score"])
        prec, rec, _ = precision_recall_curve(df["y_true"], df["anomaly_score"])
        axes[0].plot(fpr, tpr, label=name)
        axes[1].plot(rec, prec, label=name)
    axes[0].plot([0, 1], [0, 1], "k--", linewidth=0.8)
    axes[0].set_xlabel("False positive rate"); axes[0].set_ylabel("True positive rate"); axes[0].set_title("ROC")
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision"); axes[1].set_title("Precision-Recall")
    axes[0].legend(); axes[1].legend()
    _source_caption(axes[0], "Source: results/tables/detection_scores_*.csv | Mode: offline dataset evaluation (Stage 3)")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "roc_pr_curves.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Controlled local fault experiment figures (Section 6C)
# ---------------------------------------------------------------------------

def _condition_order(df: pd.DataFrame) -> list[str]:
    return [c for c in ("baseline", "rule_based", "ai_driven") if c in df["condition"].unique()]


def _plot_value_distribution(df: pd.DataFrame, value_col: str, ylabel: str, suptitle: str, out_name: str, source_text: str) -> str | None:
    """Boxplots are misleading with very few runs per cell (n=2 here collapses
    to a degenerate, near-invisible box whose black outline swallows the
    intended condition color). Below a small-n cutoff, plot the individual
    measured values as colored dots plus a mean tick instead -- this shows
    exactly what was measured rather than implying a distribution shape two
    points can't support. Falls back to a standard colored boxplot once a
    cell has enough runs (>=5) for that to be meaningful."""
    if df.empty or df[value_col].dropna().empty:
        return None
    scenarios = [s for s in SCENARIO_LABELS if s in df["scenario"].unique()]
    fig, axes = plt.subplots(1, len(scenarios), figsize=(5 * len(scenarios), 4), sharey=True)
    if len(scenarios) == 1:
        axes = [axes]
    for ax, scenario in zip(axes, scenarios):
        sub = df[df["scenario"] == scenario]
        conditions = _condition_order(sub)
        per_condition = [sub[sub["condition"] == c][value_col].dropna().values for c in conditions]
        max_n = max((len(v) for v in per_condition), default=0)

        if max_n >= 5:
            bp = ax.boxplot(per_condition, tick_labels=[CONDITION_LABELS[c] for c in conditions], patch_artist=True)
            for patch, c in zip(bp["boxes"], conditions):
                patch.set_facecolor(CONDITION_COLORS[c])
        else:
            rng = np.random.default_rng(0)
            for i, (c, values) in enumerate(zip(conditions, per_condition)):
                if len(values) == 0:
                    continue
                jitter = rng.uniform(-0.08, 0.08, size=len(values))
                ax.scatter(
                    np.full(len(values), i) + jitter, values,
                    color=CONDITION_COLORS[c], edgecolor="black", linewidth=0.6,
                    s=60, zorder=3, label=CONDITION_LABELS[c],
                )
                ax.hlines(np.mean(values), i - 0.18, i + 0.18, color=CONDITION_COLORS[c], linewidth=2.5, zorder=2)
            ax.set_xticks(range(len(conditions)))
            ax.set_xticklabels([CONDITION_LABELS[c] for c in conditions])
            ax.set_xlim(-0.5, len(conditions) - 0.5)

        ax.set_title(SCENARIO_LABELS[scenario])
        ax.set_ylabel(ylabel)
    caption = source_text
    if max_n < 5:
        caption = f"{source_text}\ndots = individual runs (n={max_n}/condition, too few for a boxplot); bar = mean"
    _source_caption(axes[0], caption)
    fig.suptitle(suptitle)
    fig.tight_layout()
    path = os.path.join(_figures_dir(), out_name)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_mttr_distributions(df: pd.DataFrame) -> str | None:
    return _plot_value_distribution(
        df, "mttr_s", "MTTR (seconds)", "MTTR across repeated runs", "mttr_distributions.png",
        "Source: results/tables/experiment_runs.csv | Mode: controlled local fault experiments (measured, real recovery)",
    )


def plot_detection_delay_distributions(df: pd.DataFrame) -> str | None:
    return _plot_value_distribution(
        df, "detection_delay_s", "Detection delay (seconds)", "Detection delay across repeated runs", "detection_delay_distributions.png",
        "Source: results/tables/experiment_runs.csv | Mode: controlled local fault experiments",
    )


def plot_mttr_heatmap(df: pd.DataFrame) -> str | None:
    cfg = load_config()
    scenarios = cfg["visualization"]["heatmap_scenarios"]
    conditions = ["baseline", "rule_based", "ai_driven"]
    if df.empty:
        return None

    matrix = np.full((len(scenarios), len(conditions)), np.nan)
    for i, scenario in enumerate(scenarios):
        for j, condition in enumerate(conditions):
            vals = df[(df["scenario"] == scenario) & (df["condition"] == condition)]["mttr_s"].dropna()
            if len(vals):
                matrix[i, j] = vals.mean()

    fig, ax = plt.subplots(figsize=(6, 4))
    # "viridis_r" so lower MTTR (faster recovery) reads as the brighter/better end
    im = ax.imshow(matrix, cmap="viridis_r")
    ax.set_xticks(range(len(conditions))); ax.set_xticklabels([CONDITION_LABELS[c] for c in conditions])
    ax.set_yticks(range(len(scenarios))); ax.set_yticklabels([SCENARIO_LABELS[s] for s in scenarios])
    for i in range(len(scenarios)):
        for j in range(len(conditions)):
            if not np.isnan(matrix[i, j]):
                ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center", color="white")
            else:
                ax.text(j, i, "n/a", ha="center", va="center", color="gray")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("MTTR (seconds) -- lower is faster recovery")
    ax.set_title("Mean MTTR by scenario x condition (in-scope scenarios only)")
    _source_caption(ax, "Source: results/tables/experiment_runs.csv | Mode: controlled local fault experiments")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "mttr_heatmap.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_availability_request_success(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    scenarios = [s for s in SCENARIO_LABELS if s in df["scenario"].unique()]
    conditions = _condition_order(df)
    width = 0.8 / max(len(conditions), 1)

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(scenarios))
    for k, condition in enumerate(conditions):
        means = []
        for scenario in scenarios:
            vals = df[(df["scenario"] == scenario) & (df["condition"] == condition)]["request_success_rate"].dropna()
            means.append(vals.mean() if len(vals) else np.nan)
        ax.bar(x + k * width, means, width, label=CONDITION_LABELS[condition], color=CONDITION_COLORS[condition])
    ax.set_xticks(x + width * (len(conditions) - 1) / 2)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])
    ax.set_ylabel("Request success rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("Request success rate during controlled local fault experiments")
    ax.legend()
    _source_caption(ax, "Source: results/tables/experiment_runs.csv | Mode: controlled local fault experiments")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "availability_request_success.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_overhead_vs_recovery(df: pd.DataFrame) -> str | None:
    sub = df.dropna(subset=["controller_decision_latency_ms_mean", "mttr_s"])
    if sub.empty:
        return None
    fig, ax = plt.subplots(figsize=(6, 4))
    for condition in _condition_order(sub):
        csub = sub[sub["condition"] == condition]
        ax.scatter(csub["controller_decision_latency_ms_mean"], csub["mttr_s"], color=CONDITION_COLORS[condition], label=CONDITION_LABELS[condition])
    ax.set_xlabel("Mean controller decision latency per run (ms)")
    ax.set_ylabel("MTTR (seconds)")
    ax.set_title("Controller overhead vs. recovery outcome")
    ax.legend()
    _source_caption(ax, "Source: results/tables/experiment_runs.csv | Mode: controlled local fault experiments")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), "overhead_vs_recovery.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_anomaly_score_timeline(example_run_json_path: str) -> str | None:
    with open(example_run_json_path) as f:
        data = json.load(f)
    r = data["run_record"]
    trace = r.get("anomaly_score_trace") or []
    if not trace:
        return None

    t0 = r["fault_injection_timestamp"]
    xs = [(p["t"] - t0) for p in trace]
    ys = [p["score"] for p in trace]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, ys, color=CONDITION_COLORS["ai_driven"], label="anomaly score")
    for label, ts in (("fault injected", r["fault_injection_timestamp"]), ("detection", r["detection_timestamp"]),
                      ("action", r["action_timestamp"]), ("recovery", r["recovery_timestamp"])):
        if ts:
            ax.axvline(ts - t0, linestyle="--", alpha=0.7)
            ax.text(ts - t0, ax.get_ylim()[1], label, rotation=90, fontsize=8, va="top")
    ax.set_xlabel("Seconds since fault injection")
    ax.set_ylabel("Anomaly score")
    ax.set_title(f"AI-driven anomaly score timeline: {r['scenario']} (run {r['run_id']})")
    _source_caption(ax, f"Source: {example_run_json_path} | Mode: controlled local fault experiment (live telemetry, not simulated)")
    fig.tight_layout()
    path = os.path.join(_figures_dir(), f"anomaly_score_timeline_{r['scenario']}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_aws_cloudwatch_descriptive() -> str | None:
    """Descriptive-only figure for the AWS CloudWatch / NAB source. No
    detection metrics are computed or implied here -- this source has no
    labels (see data_dictionary.md). One representative series per metric
    family is plotted purely to show what the raw signal looks like."""
    from src.preprocessing.adapters import load_aws_cloudwatch_all

    series = load_aws_cloudwatch_all()
    if not series:
        return None

    # pick one series per metric family (by filename prefix) for a readable panel
    chosen: dict[str, str] = {}
    for name in series:
        for prefix in ("ec2_cpu_utilization", "rds_cpu_utilization", "ec2_network_in",
                       "ec2_disk_write_bytes", "elb_request_count", "grok_asg_anomaly",
                       "iio_us-east-1"):
            if name.startswith(prefix) and prefix not in chosen:
                chosen[prefix] = name

    n = len(chosen)
    if n == 0:
        return None
    fig, axes = plt.subplots(n, 1, figsize=(9, 2.2 * n), sharex=False)
    if n == 1:
        axes = [axes]
    for ax, (prefix, name) in zip(axes, chosen.items()):
        ds = series[name]
        ax.plot(ds.df[ds.timestamp_col], ds.df[ds.value_cols[0]], color="#888888", linewidth=0.8)
        ax.set_title(name, fontsize=9, loc="left")
        ax.tick_params(labelsize=7)
    fig.suptitle(
        "AWS CloudWatch directory: representative raw series (descriptive only -- public NAB\n"
        "'realAWSCloudwatch' benchmark, UNLABELED, not this project's own environment)",
        fontsize=10,
    )
    _source_caption(
        axes[-1],
        "Source: ../data/aws_cloudwatch_metrics/*.csv | Mode: descriptive profiling only -- "
        "no detection metrics (no labels exist for this source)",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    path = os.path.join(_figures_dir(), "aws_cloudwatch_descriptive.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_all_offline_figures() -> list[str]:
    paths = [
        plot_detection_metric_comparison(),
        plot_confusion_matrices(),
        plot_roc_pr_curves(),
        plot_aws_cloudwatch_descriptive(),
    ]
    return [p for p in paths if p]


def generate_all_experiment_figures(df: pd.DataFrame) -> list[str]:
    paths = [
        plot_mttr_distributions(df),
        plot_detection_delay_distributions(df),
        plot_mttr_heatmap(df),
        plot_availability_request_success(df),
        plot_overhead_vs_recovery(df),
    ]
    return [p for p in paths if p]
