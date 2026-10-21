"""Streamlit dashboard for the self-healing dissertation pipeline.

Run with: streamlit run src/dashboard/app.py

Every view is explicitly labeled with its data source and evaluation mode
(offline dataset evaluation vs. controlled local fault experiment) so the
viewer never confuses the two (Section 6/13).
"""
from __future__ import annotations

import glob
import json
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.common.config import load_config, resolve_path  # noqa: E402
from src.experiments.aggregate import build_summary_by_condition_scenario, load_all_runs  # noqa: E402

st.set_page_config(page_title="Self-Healing Microservices Dissertation", layout="wide")
cfg = load_config()

st.title("AI-Driven Self-Healing in Cloud-Native Microservices")
st.caption(
    "Research dashboard. Figures and tables are generated from measured data only -- "
    "no illustrative or target values are shown here."
)

tab_offline, tab_experiments, tab_telemetry, tab_reports = st.tabs(
    ["Offline dataset evaluation", "Controlled local experiments", "Run telemetry explorer", "Reports"]
)

with tab_offline:
    st.header("Offline dataset evaluation (Stage 3)")
    st.caption("Mode: offline dataset evaluation. Supports detection metrics, not counterfactual recovery claims.")
    tables_dir = resolve_path(cfg["paths"]["results_tables"])
    cols = st.columns(2)
    for i, name in enumerate(("microsoft", "kaggle")):
        metrics_path = os.path.join(tables_dir, f"detection_metrics_{name}.json")
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                m = json.load(f)
            with cols[i % 2]:
                st.subheader(name)
                st.json(m)
        else:
            with cols[i % 2]:
                st.info(f"No detection metrics found for '{name}'. Run `python -m src.models.run_training` first.")

    figures_dir = resolve_path(cfg["paths"]["results_figures"])
    for fig_name in ("detection_metric_comparison.png", "confusion_matrices.png", "roc_pr_curves.png"):
        fig_path = os.path.join(figures_dir, fig_name)
        if os.path.exists(fig_path):
            st.image(fig_path)

    st.warning(
        "The AWS CloudWatch files under ../data/aws_cloudwatch_metrics match the public NAB "
        "'realAWSCloudwatch' benchmark and ship with no labels. They are used only for "
        "descriptive profiling, not detection-metric claims."
    )

with tab_experiments:
    st.header("Controlled local fault experiments (Stage 5/6)")
    st.caption("Mode: controlled local fault experiments -- real local processes, real measured recovery, not a simulation.")
    df = load_all_runs()
    if df.empty:
        st.info("No experiment runs found yet. Run `python -m src.experiments.runner --enable-real-actions` first.")
    else:
        summary = build_summary_by_condition_scenario(df)
        st.subheader("Summary by scenario x condition")
        st.dataframe(summary)

        st.subheader("All runs (nothing excluded, including unrecovered)")
        st.dataframe(df)

        figures_dir = resolve_path(cfg["paths"]["results_figures"])
        for fig_name in (
            "mttr_heatmap.png", "mttr_distributions.png", "detection_delay_distributions.png",
            "availability_request_success.png", "overhead_vs_recovery.png",
        ):
            fig_path = os.path.join(figures_dir, fig_name)
            if os.path.exists(fig_path):
                st.image(fig_path)

with tab_telemetry:
    st.header("Single-run telemetry explorer")
    logs_dir = resolve_path(cfg["paths"]["results_logs"])
    run_paths = sorted(glob.glob(os.path.join(logs_dir, "runs", "*.json")))
    if not run_paths:
        st.info("No runs found yet.")
    else:
        chosen = st.selectbox("Choose a run", run_paths, format_func=lambda p: os.path.basename(p))
        with open(chosen) as f:
            data = json.load(f)
        st.json(data["run_record"])
        telemetry_df = pd.DataFrame(data["telemetry"])
        if not telemetry_df.empty:
            st.line_chart(telemetry_df.set_index("t")[["mem_mb", "work_latency_ms"]])

with tab_reports:
    st.header("Reports")
    reports_dir = resolve_path(cfg["paths"]["results_reports"])
    for fname in sorted(os.listdir(reports_dir)) if os.path.isdir(reports_dir) else []:
        if fname.endswith(".md"):
            with open(os.path.join(reports_dir, fname)) as f:
                content = f.read()
            with st.expander(fname):
                st.markdown(content)
