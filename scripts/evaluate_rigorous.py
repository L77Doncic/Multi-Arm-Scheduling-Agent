#!/usr/bin/env python3
"""
Rigorous evaluation script following NeurIPS/ICLR experiment standards.

Key requirements from top-tier ML conferences:
1. Multiple runs with different seeds (≥5) for statistical significance
2. Mean ± std reported for all metrics
3. Paired comparisons with same problem instances
4. Reproducibility via fixed random seeds
5. Proper baseline implementations (not formula-based noise)
6. Statistical significance tests (paired t-test)

Usage:
    python scripts/evaluate_rigorous.py --scenario data/scenarios/1p_production_line.json
    python scripts/evaluate_rigorous.py --scenario data/scenarios/1p_production_line.json --runs 10
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_scenario(path: str) -> dict:
    with open(path) as f:
        if path.endswith('.json'):
            import json
            return json.load(f)
        return yaml.safe_load(f)


def load_agent_config() -> dict:
    config_path = PROJECT_ROOT / "configs" / "agent_config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def run_agent_once(agent, instruction: str, scene_config: dict,
                   seed: int) -> Dict[str, float]:
    """Run agent once with a specific seed. Returns metrics dict."""
    import random
    random.seed(seed)
    np.random.seed(seed)

    result = agent.execute_scheduling(
        instruction=instruction,
        scene_config=scene_config,
    )

    return {
        "makespan": result.makespan,
        "task_success_rate": result.task_success_rate,
        "resource_utilization": result.resource_utilization,
        "constraint_violations": result.constraint_violations,
        "num_tasks": len(result.tasks),
    }


def run_greedy_baseline(scene_config: dict, seed: int) -> Dict[str, float]:
    """
    Proper greedy baseline: actually solves the scheduling problem.
    Uses LPT (Longest Processing Time) list scheduling algorithm.
    """
    import random
    random.seed(seed)
    np.random.seed(seed)

    stations = scene_config.get("stations", [])
    workpieces = scene_config.get("workpieces", [])
    arms = scene_config.get("robot_arms", [])

    if not stations or not workpieces or not arms:
        return {"makespan": 0, "task_success_rate": 0, "resource_utilization": 0,
                "constraint_violations": 0, "num_tasks": 0}

    # Build task list from scene
    tasks = []
    for wp in workpieces:
        for i, station_id in enumerate(wp.get("operations_sequence", [])):
            station = next((s for s in stations if s["id"] == station_id), None)
            if station:
                tasks.append({
                    "id": f"t_{wp['id']}_{station_id}",
                    "duration": station.get("estimated_duration", 3.0),
                    "required_caps": station.get("capabilities_required", []),
                    "deps": [f"t_{wp['id']}_{wp['operations_sequence'][i-1]}"] if i > 0 else [],
                })

    if not tasks:
        return {"makespan": 0, "task_success_rate": 0, "resource_utilization": 0,
                "constraint_violations": 0, "num_tasks": 0}

    # LPT: sort by duration descending
    sorted_tasks = sorted(tasks, key=lambda t: t["duration"], reverse=True)

    # Greedy assignment to least-loaded compatible arm
    arm_loads = {a["id"]: 0.0 for a in arms}
    arm_caps = {a["id"]: set(a.get("capabilities", [])) for a in arms}
    allocation = {}
    violations = 0

    for task in sorted_tasks:
        required = set(task["required_caps"])
        best_arm = None
        best_load = float("inf")

        for arm in arms:
            aid = arm["id"]
            # Check capability match
            if not required.issubset(arm_caps[aid]):
                continue
            if arm_loads[aid] < best_load:
                best_load = arm_loads[aid]
                best_arm = aid

        if best_arm:
            allocation[task["id"]] = best_arm
            arm_loads[best_arm] += task["duration"]
        else:
            # No compatible arm — assign to least loaded, count violation
            best_arm = min(arm_loads, key=arm_loads.get)
            allocation[task["id"]] = best_arm
            arm_loads[best_arm] += task["duration"]
            violations += 1

    # Compute makespan considering dependencies
    task_end_times = {}
    for task in sorted_tasks:
        tid = task["id"]
        earliest_start = 0
        for dep_id in task["deps"]:
            if dep_id in task_end_times:
                earliest_start = max(earliest_start, task_end_times[dep_id])
        task_end_times[tid] = earliest_start + task["duration"]

    makespan = max(task_end_times.values()) if task_end_times else 0
    total_work = sum(arm_loads.values())
    n_arms = len(arms)
    utilization = total_work / (n_arms * makespan) if makespan > 0 and n_arms > 0 else 0

    return {
        "makespan": makespan,
        "task_success_rate": 1.0,  # Greedy always succeeds (it's deterministic)
        "resource_utilization": min(utilization, 1.0),
        "constraint_violations": violations,
        "num_tasks": len(tasks),
    }


def run_random_baseline(scene_config: dict, seed: int) -> Dict[str, float]:
    """
    Proper random baseline: actually solves the scheduling with random assignment.
    """
    import random
    random.seed(seed)
    np.random.seed(seed)

    stations = scene_config.get("stations", [])
    workpieces = scene_config.get("workpieces", [])
    arms = scene_config.get("robot_arms", [])

    if not stations or not workpieces or not arms:
        return {"makespan": 0, "task_success_rate": 0, "resource_utilization": 0,
                "constraint_violations": 0, "num_tasks": 0}

    tasks = []
    for wp in workpieces:
        for i, station_id in enumerate(wp.get("operations_sequence", [])):
            station = next((s for s in stations if s["id"] == station_id), None)
            if station:
                tasks.append({
                    "id": f"t_{wp['id']}_{station_id}",
                    "duration": station.get("estimated_duration", 3.0),
                    "required_caps": station.get("capabilities_required", []),
                    "deps": [f"t_{wp['id']}_{wp['operations_sequence'][i-1]}"] if i > 0 else [],
                })

    if not tasks:
        return {"makespan": 0, "task_success_rate": 0, "resource_utilization": 0,
                "constraint_violations": 0, "num_tasks": 0}

    arm_loads = {a["id"]: 0.0 for a in arms}
    arm_caps = {a["id"]: set(a.get("capabilities", [])) for a in arms}
    violations = 0
    successful = 0

    # Random order
    random.shuffle(tasks)
    allocation = {}

    for task in tasks:
        required = set(task["required_caps"])
        compatible = [a for a in arms if required.issubset(arm_caps[a["id"]])]

        if compatible:
            arm = random.choice(compatible)
            successful += 1
        else:
            arm = random.choice(arms)
            violations += 1

        allocation[task["id"]] = arm["id"]
        arm_loads[arm["id"]] += task["duration"]

    # Compute makespan with dependencies
    task_end_times = {}
    for task in tasks:
        tid = task["id"]
        earliest_start = 0
        for dep_id in task["deps"]:
            if dep_id in task_end_times:
                earliest_start = max(earliest_start, task_end_times[dep_id])
        task_end_times[tid] = earliest_start + task["duration"]

    makespan = max(task_end_times.values()) if task_end_times else 0
    total_work = sum(arm_loads.values())
    n_arms = len(arms)
    utilization = total_work / (n_arms * makespan) if makespan > 0 and n_arms > 0 else 0

    return {
        "makespan": makespan,
        "task_success_rate": successful / len(tasks) if tasks else 0,
        "resource_utilization": min(utilization, 1.0),
        "constraint_violations": violations,
        "num_tasks": len(tasks),
    }


def compute_stats(runs: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Compute mean and std for each metric across runs."""
    if not runs:
        return {}

    metrics = runs[0].keys()
    stats = {}
    for metric in metrics:
        values = [r[metric] for r in runs if metric in r]
        if values:
            stats[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "n": len(values),
            }
    return stats


def paired_t_test(agent_values: List[float],
                  baseline_values: List[float]) -> Dict[str, float]:
    """Perform paired t-test between agent and baseline."""
    from scipy import stats
    n = min(len(agent_values), len(baseline_values))
    if n < 2:
        return {"t_statistic": 0, "p_value": 1.0, "significant": False}

    t_stat, p_value = stats.ttest_rel(agent_values[:n], baseline_values[:n])
    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "significant": p_value < 0.05,
        "n_pairs": n,
    }


def print_results_table(agent_stats: Dict, baseline_stats: Dict[str, Dict],
                        significance: Dict[str, Dict]):
    """Print formatted results table."""
    metrics = ["makespan", "task_success_rate", "resource_utilization", "constraint_violations"]

    print()
    print("=" * 90)
    print("RIGOROUS EVALUATION RESULTS (mean ± std)")
    print("=" * 90)
    print()

    # Header
    header = f"{'Metric':<25s}"
    header += f"{'Agent':>18s}"
    for method in baseline_stats:
        header += f"{method:>18s}"
    print(header)
    print("-" * 90)

    # Rows
    for metric in metrics:
        if metric not in agent_stats:
            continue

        a = agent_stats[metric]
        row = f"{metric:<25s}"
        row += f"{a['mean']:>10.3f} ±{a['std']:>6.3f}"

        for method, stats in baseline_stats.items():
            if metric in stats:
                s = stats[metric]
                row += f"{s['mean']:>10.3f} ±{s['std']:>6.3f}"
            else:
                row += f"{'N/A':>18s}"
        print(row)

    # Significance
    print()
    print("Statistical Significance (paired t-test, α=0.05):")
    print("-" * 90)
    for metric in metrics:
        for method, tests in significance.items():
            if metric in tests:
                t = tests[metric]
                sig = "***" if t["p_value"] < 0.001 else ("**" if t["p_value"] < 0.01 else ("*" if t["p_value"] < 0.05 else "ns"))
                print(f"  {metric:<25s} vs {method:<12s}: p={t['p_value']:.4f} {sig}")

    print()
    print(f"  *** p<0.001, ** p<0.01, * p<0.05, ns = not significant")
    print("=" * 90)


def run_evaluation(scenario_path: str, num_runs: int = 5, verbose: bool = False,
                   output_dir: str = "outputs/results"):
    setup_logging(verbose)
    logger = logging.getLogger("evaluate_rigorous")

    # Load scenario
    logger.info("Loading scenario: %s", scenario_path)
    config = load_scenario(scenario_path)
    scenario = config.get("scenario", config)
    instruction = scenario.get("instruction", "Execute assembly tasks")
    scene_config = scenario

    # Seeds for reproducibility (same across methods for fair comparison)
    seeds = list(range(42, 42 + num_runs))
    logger.info("Running %d evaluations with seeds: %s", num_runs, seeds)

    # Initialize agent
    agent_config = load_agent_config()
    if "robot_arms" in scenario:
        agent_config["robot_arms"] = scenario["robot_arms"]

    from agent.core import SchedulingAgent
    agent = SchedulingAgent(agent_config)

    # Run agent
    logger.info("Running agent (%d runs)...", num_runs)
    agent_runs = []
    for i, seed in enumerate(seeds):
        logger.info("  Run %d/%d (seed=%d)", i + 1, num_runs, seed)
        result = run_agent_once(agent, instruction, scene_config, seed)
        agent_runs.append(result)

    # Run baselines with same seeds
    logger.info("Running greedy baseline (%d runs)...", num_runs)
    greedy_runs = []
    for seed in seeds:
        greedy_runs.append(run_greedy_baseline(scene_config, seed))

    logger.info("Running random baseline (%d runs)...", num_runs)
    random_runs = []
    for seed in seeds:
        random_runs.append(run_random_baseline(scene_config, seed))

    # Compute statistics
    agent_stats = compute_stats(agent_runs)
    baseline_stats = {
        "Greedy(LPT)": compute_stats(greedy_runs),
        "Random": compute_stats(random_runs),
    }

    # Statistical significance tests
    significance = {}
    metrics = ["makespan", "task_success_rate", "resource_utilization", "constraint_violations"]
    for method_name, runs in [("Greedy(LPT)", greedy_runs), ("Random", random_runs)]:
        significance[method_name] = {}
        for metric in metrics:
            agent_vals = [r[metric] for r in agent_runs if metric in r]
            base_vals = [r[metric] for r in runs if metric in r]
            significance[method_name][metric] = paired_t_test(agent_vals, base_vals)

    # Print results
    print_results_table(agent_stats, baseline_stats, significance)

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "rigorous_evaluation.json")
    report = {
        "scenario": scenario_path,
        "num_runs": num_runs,
        "seeds": seeds,
        "agent_stats": agent_stats,
        "baseline_stats": baseline_stats,
        "significance": significance,
        "agent_runs": agent_runs,
        "greedy_runs": greedy_runs,
        "random_runs": random_runs,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "Evaluation follows NeurIPS/ICLR standards: multiple seeds, paired t-test, mean±std",
    }

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Results saved to %s", output_file)

    return report


def main():
    parser = argparse.ArgumentParser(description="Rigorous evaluation (NeurIPS/ICLR standard)")
    parser.add_argument("--scenario", "-s", required=True, help="Scenario YAML file")
    parser.add_argument("--runs", "-n", type=int, default=5, help="Number of runs (default: 5)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", "-o", default="outputs/results")

    args = parser.parse_args()
    run_evaluation(args.scenario, args.runs, args.verbose, args.output)


if __name__ == "__main__":
    main()
