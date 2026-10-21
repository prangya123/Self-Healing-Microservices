# Data Dictionary

All field meanings below were confirmed by direct inspection of the files in
`../data/` (see `results/reports/dataset_inspection_report.md`), not assumed
in advance.

## 1. Microsoft Cloud Monitoring (`../data/cloud_monitoring_sample.csv`)

| Column | Type | Meaning |
|---|---|---|
| `TimeStamp` | datetime (naive) | Hourly timestamp. |
| `Value` | int | Single univariate monitored metric. The source does not name the metric (e.g. requests, CPU, latency) -- it is used as an unlabeled generic signal, not attributed to a specific resource type. |
| `Label` | int (0/1) | Generic anomaly flag. 0 = normal, 1 = anomaly. **Does not indicate fault type** (crash vs. memory vs. dependency) -- this is a binary "anomalous or not" label only. |

- 710 rows, hourly cadence, 2018-06-19 to 2018-07-18.
- No service/host identifier (single series).
- 13 duplicate rows (dropped during cleaning, see preprocessing report).

## 2. Kaggle Cloud Resource Usage (`../data/kaggle_cloud_resource_usage.csv`)

| Column | Meaning |
|---|---|
| `time` | Minute-level timestamp, UTC. |
| `node_cpu_utilization\|Average\|node1` | CPU utilization (%), node1. |
| `node_cpu_utilization\|Average\|node2` | CPU utilization (%), node2. |
| `pod_memory_utilization\|Average\|carts-db` | Memory utilization of the `carts-db` pod. |
| `pod_network_rx_bytes\|Average\|user` | Network bytes received by the `user` service's pod. |
| `carts_req_rate` | Request rate to the `carts` service. |
| `user_req_rate` | Request rate to the `user` service. |
| `orders_perc95_rt` | 95th-percentile response time, `orders` service. |
| `front-end_perc95_rt` | 95th-percentile response time, `front-end` service. |
| `anomaly` | Generic anomaly flag (0/1), global to the row, not per-service. **Does not indicate fault type.** |

Column names follow a `metric|aggregation|entity` convention, indicating the
underlying telemetry was pivoted from multiple services/pods of what appears
to be a microservices demo application (carts, orders, front-end, user) into
one wide row per minute. Services are inferred from column name suffixes
only -- no separate service-identifier column exists.

- 10,080 rows, 1-minute cadence, 2024-05-13 to 2024-05-20 (~7 days).
- No duplicates, no missing values.

## 3. AWS CloudWatch Metrics (`../data/aws_cloudwatch_metrics/*.csv`)

| Column | Meaning |
|---|---|
| `timestamp` | 5-minute-cadence timestamp (naive). |
| `value` | Single univariate metric per file (CPU %, network bytes, disk write bytes, or request count depending on filename). |

**Important provenance note (confirmed with user 2026-10-20):** these 17
files' names (e.g. `ec2_cpu_utilization_825cc2.csv`, `grok_asg_anomaly.csv`,
`iio_us-east-1_i-a2eb1cd9_NetworkIn.csv`) match the public **NAB (Numenta
Anomaly Benchmark) "realAWSCloudwatch"** corpus from 2014, not a fresh export
from the user's own 2026 experimental environment. No label file
(`combined_windows.json` or similar) accompanies them, so they are
**unlabeled**. They are used only for descriptive/unsupervised profiling in
this project, never for detection precision/recall/F1 claims.

Each file is an independent series (different EC2/RDS/ELB instance, 2013-2014
time ranges that do not all overlap) -- there is no shared service identifier
linking them into one application's telemetry, so they are never concatenated
or treated as one multivariate dataset.

## 4. Local application telemetry (generated live, not a static file)

Produced by `src/app/telemetry.py` (`TelemetryRecord`) while the FastAPI
testbed (`src/app/main_service.py`, `src/app/dependency_service.py`) is
running during a controlled local experiment (Section 6C).

| Field | Meaning |
|---|---|
| `t` | Seconds since the telemetry collector started (monotonic clock). |
| `wall_time` | `time.time()` at poll. |
| `health_reachable` | Whether `GET /health` returned 200. False means the process is down (crash) or returning a simulated resource-exhaustion failure (severe unmitigated memory leak). |
| `cpu_percent`, `mem_mb` | Process-level CPU/RSS memory of the app worker, from `psutil`. |
| `circuit_breaker_open` | Whether the app's dependency circuit breaker is currently open. |
| `leaked_mb` | Ground-truth bytes allocated by the memory-leak fault injector (0 unless that scenario is active). |
| `work_success` | Whether `GET /work` returned 200 (includes both normal and degraded-fallback responses). |
| `work_latency_ms` | Wall-clock latency of the `/work` call. |
| `work_mode` | `"normal"` (dependency called directly), `"degraded_fallback"` (circuit breaker open), or `None` (request failed outright). **`degraded_fallback` is never treated as full recovery.** |

## 5. Run records (`results/logs/runs/*.json`)

One `RunRecord` (see `src/controllers/types.py`) per controlled local fault
experiment: run ID, scenario, condition, seed, workload config, fault
injection/detection/action/recovery timestamps, recovery success,
manual-intervention flag, actions taken, degraded-operation seconds, request
counts, controller decision latency, and (AI-driven only) the anomaly score
trace. Full raw telemetry for the run is stored alongside it.
