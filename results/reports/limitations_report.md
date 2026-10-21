# Limitations Report

This report lists known weaknesses of the evidence produced by this
implementation, organized by the stage that introduces them. It should be
read alongside `dissertation_results_summary.md`.

## Dataset limitations

1. **AWS CloudWatch source is not what it was assumed to be.** The 17 files
   under `../data/aws_cloudwatch_metrics/` match the public NAB
   "realAWSCloudwatch" benchmark (2013-2014), not a fresh export from the
   user's own 2026 environment, and carry no label file. Confirmed with the
   user on 2026-10-20. Consequence: this source supports descriptive
   profiling only, not detection-metric claims, and is not usable as
   "operational validation" evidence for this dissertation's own system.

2. **No dataset carries fault-type labels.** Microsoft and Kaggle both have a
   single generic binary anomaly flag. Neither distinguishes crash vs.
   memory-leak vs. dependency-timeout. Offline detection metrics (precision,
   recall, F1, ROC-AUC, PR-AUC) therefore measure *generic anomaly
   detection*, not scenario-specific fault detection. The only
   scenario-specific detection/recovery evidence in this project comes from
   the controlled local fault experiments (Stage 6C), which inject labeled
   faults directly.

3. **Microsoft dataset is small.** 710 rows (~29 days, hourly), 409/121/123
   rows after the chronological train/val/test split and feature-window
   drop. Detection metrics on this split should be read as indicative, not
   as a precise population estimate.

4. **Kaggle anomaly label is a single global flag** across 8 multivariate
   columns spanning multiple inferred services (carts, orders, front-end,
   user, node1/node2). It cannot localize *which* service or metric was
   anomalous, which likely explains the detector's much lower F1 on this
   dataset (0.354 measured, vs. 0.827 on Microsoft) relative to a
   single-series problem: Isolation Forest sees one combined anomaly score
   across heterogeneous, differently-scaled signals.

5. **No cross-dataset detector transfer was performed or attempted** (by
   design, per the dissertation scope): Microsoft, Kaggle, and the local app
   telemetry each have incompatible feature spaces and each get their own
   model. This avoids a (likely invalid) assumption, at the cost of not
   producing a single unified detection number across sources.

## Model limitations

6. **Isolation Forest is not a temporal/sequence model.** All temporal
   context comes from engineered lag/rolling-mean/rolling-std/rate-of-change
   features. This is disclosed explicitly in model metadata
   (`models/*/metadata.json`) and must not be described as an LSTM or any
   other deep sequence model in the dissertation text.

7. **The local-app AI detector's threshold is not F1-tuned.** Unlike the
   offline Microsoft/Kaggle detectors (threshold chosen by grid-searching F1
   on a labeled validation split), the live local-app detector has no
   fault-labeled data available (it is trained purely on normal-operation
   telemetry -- no fault is ever injected during training collection). Its
   threshold is the 99th percentile of its own training scores. This is a
   materially weaker threshold-selection method and is disclosed in
   `models/local_app/metadata.json`. Unaffected by item 8's history below.

8. **RESOLVED, but documented because it materially changed the measured
   result.** The local-app AI detector was originally retrained from scratch
   on each run's own ~20-second, ~16-20-row warmup telemetry. This was found
   to be unreliable: in one run the anomaly score trended *downward*
   throughout an active, real memory leak and never crossed threshold
   (detection only happened via the unrelated hard-failure health check);
   in another dependency-timeout run, the score never crossed threshold at
   all and zero actions were taken, behavior indistinguishable from
   baseline. Root-causing this surfaced a genuine confound in the
   application under test (`main_service.py` created a new
   `httpx.AsyncClient()` per `/work` call, causing a ~20MB, 25-second RSS
   creep unrelated to any fault -- fixed by reusing one client) and a
   genuinely undersized per-run training set. **Current design**: the
   detector is trained ONCE, offline, on 4 pooled 90-second normal-operation
   sessions (336 rows; `src/controllers/collect_normal_telemetry.py`) and
   reused (frozen) across all runs, the same pattern used for the
   Microsoft/Kaggle offline detectors. Validated against held-out control
   checks (0/56 false positives over 60s of normal operation; consistent
   sub-0.1s detection of a manually-injected leak) before any affected
   experiment run was redone. See `results/reports/
   dissertation_results_summary.md` "Methodology correction" section for
   the full before/after comparison and the numbers this changed.

8a. **Remaining, disclosed nuance in the current (fixed) detector's
    behavior:** its anomaly score is sensitive to the *rate of change* of
    memory/latency features (via the engineered rate-of-change/rolling
    features), not just their absolute level. In manual control testing,
    the score fell back *below* threshold once an injected leak's growth
    plateaued (hit its configured cap) even though absolute memory
    remained far above normal (see the manual verification transcript
    referenced in the project history). In the experiments actually run,
    this did not matter -- the mem_mb_threshold-gated restart always fired
    while the leak was still actively growing -- but a fault that degrades
    gradually and then plateaus *below* any configured hard threshold could
    go undetected by the anomaly score alone after the initial transient.
    This is a property of using rate-of-change features for a level-based
    problem, not a training-data issue, and would need level-sensitive
    features (e.g. absolute deviation from the training mean) added
    alongside the rate-based ones to close.

## Experimental design limitations

9. **Workload is simplified.** Each telemetry poll (interval =
   `application.telemetry_interval_seconds`, default 1s) doubles as the
   single workload request against `/work`. There is no independent,
   higher-rate load generator. `config.yaml: application.workload` exists
   but is not currently wired to a separate request stream.

10. **"Recovery" required explicit gating logic to be meaningful for the
    memory-leak scenario.** A gradually growing RSS does not, by itself,
    fail the generic health/work checks used to define "N consecutive
    successes" -- it only does so once a configured resource-exhaustion
    ceiling (`fault_scenarios: memory_leak.hard_failure_mem_mb`, 220MB RSS)
    is crossed. Recovery for this scenario therefore requires evidence that
    a restart actually occurred (`_action_precondition_met` in
    `src/experiments/run_single.py`), and is evaluated only on telemetry
    collected *after* that restart. Without this, an unmitigated, still-
    growing leak that hadn't yet crossed the hard-failure ceiling would be
    misreported as "already recovered." This is a deliberate, documented
    fix, not a hidden assumption -- but it does mean memory-leak MTTR is
    sensitive to where `hard_failure_mem_mb` and `controller_thresholds.
    mem_mb_threshold` are set, and those were chosen by a single baseline
    RSS measurement (~57MB) on the development machine, not calibrated
    across hardware.

10a. **Memory-leak RSS measurement is noisy on macOS even after a fix.** The
    fault injector originally allocated zero-filled `bytearray(n)` buffers,
    which can be backed by a shared copy-on-write zero page and never
    actually increase resident memory -- this made the very first batch of
    memory-leak runs unusable (baseline and AI-driven showed implausible,
    non-monotonic RSS and were re-run after the fix) and was corrected to
    `bytearray(os.urandom(n))`, which forces real page commits
    (`src/app/main_service.py: _leak_loop`). Even after that fix, measured
    RSS still shows occasional drops of 10-30MB mid-run (visible in
    `results/logs/runs/memory_leak_*.json` telemetry), consistent with
    macOS's background memory compression. This is a real property of
    running this experiment on macOS, not a code bug, but it means
    memory-leak timing numbers have more run-to-run noise than the other two
    scenarios, and a Linux host (no transparent memory compression by
    default) would likely show cleaner, more monotonic RSS growth.

11. **Dependency-timeout "recovery" is bottlenecked by the simulated
    dependency's own recovery time** (`fault_scenarios: dependency_timeout.
    duration_seconds`, 20s), not by controller speed. Measured smoke-test
    data shows rule-based's full MTTR for this scenario was *not* shorter
    than baseline's, because both must wait for the same simulated downstream
    recovery; rule-based/AI's measured benefit here is in request-success
    rate and degraded-operation accounting during the outage, not MTTR. This
    is a genuine, not-assumed, finding -- see the results summary -- but it
    means MTTR alone is an incomplete metric for this scenario.

12. **`excess_actions` is a coarse proxy**, not a causal attribution, for
    "unnecessary actions" (Section 12): it counts restarts/breaker-opens
    beyond the first per run, which conflates legitimate repeated action
    (e.g. a second restart after a flapping dependency) with true
    overreaction.

13. **Sample size.** Numbers reported anywhere in this project unless stated
    otherwise come from a small smoke-test batch (`experiments.
    smoke_test_repeats` / the `--repeats` value actually used -- see the run
    manifest in `results/logs/manifest_*.json` for the exact count). This
    verifies the harness works end-to-end; it is explicitly **not** a
    sufficient statistical sample for a dissertation-level causal claim. A
    full run requires raising `experiments.full_repeats` and budgeting
    several runs x ~20-90 seconds each of wall-clock time.

## Not implemented (explicitly out of scope or deferred)

14. Permutation importance / feature-importance figure (Section 13, item 10)
    was not implemented -- it is explicitly optional in the brief and was
    deprioritized given project scope.

15. Docker Compose deployment is authored (`docker-compose.yml`, `Dockerfile`)
    but **not executed or verified** in the build environment, which has no
    Docker installed (confirmed with the user, who chose native local-process
    mode for verified execution). The native mode is what the test suite and
    `src/experiments/runner.py` actually exercise.

16. Statistical inference (paired resampling, effect sizes, confidence
    intervals) described in Section 12 is not yet implemented on top of the
    aggregated run table (`results/tables/experiment_runs.csv`); only
    descriptive sample statistics (mean/median/std/count) are currently
    computed in `src/experiments/aggregate.py`. This should be added before
    any significance-style claim is made in the dissertation text.
