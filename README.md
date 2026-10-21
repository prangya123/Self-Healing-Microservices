# AI-Driven Self-Healing in Cloud-Native Microservices
# Copy Rights
# Author: Prangya Parmita Kar

Research codebase for a dissertation evaluating whether AI-driven self-healing
improves fault detection, recovery efficiency, and service availability
compared with baseline and rule-based recovery, across three in-scope fault
scenarios: container/service crash, memory leak, and dependency timeout.

This README documents what was actually built and measured. See
`results/reports/limitations_report.md` for known weaknesses and
`results/reports/dissertation_results_summary.md` for the honest,
evidence-based verdict on the research hypothesis.

## What this is NOT

- Not a claim that AI outperforms rule-based recovery by default -- see the
  results summary for the actual (mixed) measured outcome.
- Not evidence from a production AWS environment: the files under
  `../data/aws_cloudwatch_metrics/` are the public, unlabeled NAB benchmark,
  not an export from a live system (confirmed with the user; see the data
  dictionary).
- Not Kubernetes, reinforcement learning, an LLM, or a deep sequence model.
  The anomaly detector is `sklearn.ensemble.IsolationForest`; temporal
  context comes entirely from engineered lag/rolling/rate-of-change features.

## Repository layout

```
config.yaml                   single source of truth for all tunables
src/
  data_inspection/             Stage 1: profiles the raw data files as-is
  preprocessing/                Stage 2: adapters, causal features, leakage-safe splits
  models/                       Stage 3: Isolation Forest training + test evaluation
  app/                          Stage 4: FastAPI service, dependency service, telemetry
  controllers/                  Stage 4: baseline / rule-based / AI-driven controllers,
                                 guarded action executor, local telemetry anomaly detector
  experiments/                  Stage 5/6: process orchestration, fault injection,
                                 single-run + repeated-run experiment drivers,
                                 aggregation, plotting
  dashboard/                    Streamlit dashboard
tests/                          pytest suite (unit + real-process integration)
results/
  tables/, figures/, logs/, reports/   generated artifacts (see below)
models/                         trained model artifacts (joblib + metadata.json)
data_dictionary/                data dictionary
docker-compose.yml, Dockerfile  optional containerized deployment (untested in
                                 the build sandbox -- no Docker there; the
                                 native local-process mode below is what the
                                 test suite and experiments actually use)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expects sibling data directories at `../data/cloud_monitoring_sample.csv`,
`../data/kaggle_cloud_resource_usage.csv`, `../data/aws_cloudwatch_metrics/*.csv`
relative to this project directory (see `config.yaml: paths`).

## Running the pipeline, stage by stage

```bash
# Stage 1: dataset inspection report (no assumptions about schema/labels)
python3 -m src.data_inspection.inspect_datasets

# Stage 2+3: leakage-safe preprocessing + Isolation Forest train/val/test
python3 -m src.preprocessing.run_preprocessing
python3 -m src.models.run_training

# Stage 4: build the fixed AI anomaly detector (once; required before any
# AI-driven experiment run). Starts/stops real local processes several times
# with no fault injected to collect normal-operation telemetry.
python3 -m src.controllers.collect_normal_telemetry

# Stage 5: controlled local fault experiments (real local processes)
# Dry run (no remediation actually executed, decisions/detection still measured):
python3 -m src.experiments.runner --repeats 2
# Real remediation, smoke test (NOT statistically sufficient, just verifies the harness):
python3 -m src.experiments.runner --smoke --enable-real-actions
# Full run (edit experiments.full_repeats in config.yaml for your sample size):
python3 -m src.experiments.runner --enable-real-actions

# Stage 6: aggregate + plot
python3 -m src.experiments.aggregate
python3 -c "from src.experiments.plotting import generate_all_offline_figures, generate_all_experiment_figures; from src.experiments.aggregate import load_all_runs; generate_all_offline_figures(); generate_all_experiment_figures(load_all_runs())"

# Dashboard
streamlit run src/dashboard/app.py
```

## Tests

```bash
python3 -m pytest tests/ -v
```

The suite includes real-process integration behavior exercised manually
during development (subprocess start/kill/restart, real HTTP fault
injection); `tests/test_aggregate.py` runs against whatever real run data
exists in `results/logs/runs/`.

## Safety

Remediation defaults to **dry-run**. Real actions require
`--enable-real-actions` on the CLI (overrides `safety.enable_real_actions`
for that process only; the checked-in `config.yaml` default stays `false`).
Guardrails enforced regardless: service allowlist, action cooldown, max
actions/restarts per run, execution timeout, a stop-switch file
(`results/logs/STOP`), and a structured JSONL audit log per run
(`results/logs/audit_<run_id>.jsonl`). AWS access, if ever added, is
read-only by design; no live AWS infrastructure is modified by this code.

## Experimental conditions

- **Baseline** (`src/controllers/baseline.py`): restart on a single failed
  health check. No memory/dependency monitoring, no circuit breaker.
- **Rule-based** (`src/controllers/rule_based.py`): explicit, configurable
  thresholds (`config.yaml: controller_thresholds`) for crash, memory, and
  dependency-failure detection, plus a circuit breaker with a half-open probe.
- **AI-driven** (`src/controllers/ai_controller.py`): an Isolation Forest
  trained ONCE, offline, on a pooled corpus of normal-operation telemetry
  (`src/controllers/collect_normal_telemetry.py`) and frozen/reused across
  all runs -- the same pattern as the Microsoft/Kaggle offline detectors.
  (An earlier per-run-retraining design was found to be unreliable and was
  replaced; see `results/reports/limitations_report.md` item 8 for the
  full story.) A crash is still checked directly (no resource telemetry
  exists once a process is down, so it can't be ML-scored). For live,
  reachable telemetry, the SAME diagnostic rules used by rule-based
  (`src/controllers/common.py: classify_degradation`) decide the action
  once the anomaly score crosses a frozen threshold -- this isolates the
  comparison to "learned trigger vs. threshold trigger," not a different
  action policy. When the score is high but no specific cause is supported
  by diagnostics, the incident is logged instead of acting (Section 9:
  anomaly detection alone never selects a disruptive action). Measured
  result: AI-driven detects gradual-onset faults (memory leak, dependency
  timeout) markedly faster than rule-based, without yet improving MTTR over
  it -- see `results/reports/dissertation_results_summary.md`.

## Known simplifications (see limitations report for full list)

- Each telemetry poll doubles as the workload request (`/work` call), i.e.
  the workload is implicitly `1 / telemetry_interval_seconds` req/s.
- The AI detector's threshold is a percentile of its own training scores,
  not F1-tuned (no fault-labeled data exists for this source), and its
  rate-of-change-sensitive features mean a fault that plateaus below a hard
  threshold after an initial transient could go undetected (limitations
  report item 8a).
- `excess_actions` (a proxy for "unnecessary actions") is a simple count
  heuristic (restarts/breaker-opens beyond the first), not a causal
  attribution of which specific action was unnecessary.
