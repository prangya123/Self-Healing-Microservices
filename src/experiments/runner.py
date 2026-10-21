"""Stage 5 CLI: run (possibly repeated) controlled local fault experiments
across all three conditions and the three in-scope scenarios, and write a
machine-readable run manifest alongside each run's record.

Usage:
    python3 -m src.experiments.runner --repeats 3 --enable-real-actions
    python3 -m src.experiments.runner --repeats 20 --enable-real-actions --conditions rule_based ai_driven

A smoke run (small --repeats) verifies the harness works end-to-end; it is
NOT a sufficient statistical sample for a dissertation claim (Section 11).
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid

from src.common.config import load_config, resolve_path
from src.controllers.types import Condition, Scenario
from src.experiments.run_single import run_single_experiment, save_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=None, help="Overrides experiments.full_repeats in config.yaml")
    parser.add_argument("--smoke", action="store_true", help="Use experiments.smoke_test_repeats instead")
    parser.add_argument("--conditions", nargs="+", default=None, choices=[c.value for c in Condition])
    parser.add_argument("--scenarios", nargs="+", default=None, choices=[s.value for s in Scenario])
    parser.add_argument(
        "--enable-real-actions", action="store_true",
        help="Required to actually execute remediation actions. Without this flag, "
             "every run executes in dry-run mode (decisions and detection are still "
             "measured, but nothing is restarted/opened, so recovery will not occur).",
    )
    args = parser.parse_args()

    cfg = load_config()
    if args.repeats is not None:
        repeats = args.repeats
    elif args.smoke:
        repeats = cfg["experiments"]["smoke_test_repeats"]
    else:
        repeats = cfg["experiments"]["full_repeats"]

    conditions = [Condition(c) for c in (args.conditions or cfg["experiments"]["conditions"])]
    scenarios = [Scenario(s) for s in (args.scenarios or cfg["experiments"]["scenarios"])]

    manifest_id = f"manifest_{uuid.uuid4().hex[:8]}"
    manifest = {
        "manifest_id": manifest_id,
        "created_at": time.time(),
        "repeats": repeats,
        "is_smoke_test": bool(args.smoke),
        "enable_real_actions": args.enable_real_actions,
        "conditions": [c.value for c in conditions],
        "scenarios": [s.value for s in scenarios],
        "random_seed_base": cfg["random_seed"],
        "config_snapshot": cfg,
        "runs": [],
    }

    if not args.enable_real_actions:
        print(
            "WARNING: --enable-real-actions not set. Runs will execute in DRY-RUN mode: "
            "decisions/detection are measured but no remediation is actually performed, "
            "so recovery_succeeded will be False for every faulted run."
        )

    total = len(conditions) * len(scenarios) * repeats
    done = 0
    for scenario in scenarios:
        for condition in conditions:
            for i in range(repeats):
                seed = cfg["random_seed"] + i
                run_id = f"{scenario.value}_{condition.value}_{seed}_{uuid.uuid4().hex[:6]}"
                print(f"[{done + 1}/{total}] running {run_id} ...")
                record, telemetry = run_single_experiment(
                    scenario, condition, seed=seed, run_id=run_id,
                    enable_real_actions=args.enable_real_actions,
                )
                path = save_run(record, telemetry)
                manifest["runs"].append({"run_id": run_id, "path": path})
                print(
                    f"    recovery_succeeded={record.recovery_succeeded} "
                    f"manual_intervention_required={record.manual_intervention_required}"
                )
                done += 1

    logs_dir = resolve_path(cfg["paths"]["results_logs"])
    manifest_path = os.path.join(logs_dir, f"{manifest_id}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\nManifest written to {manifest_path}")


if __name__ == "__main__":
    main()
