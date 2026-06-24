#!/usr/bin/env python3
"""Run all MRTA-Benchmark experiments using subprocess isolation.
Each experiment runs in a separate process (Isaac Sim requires this)."""
import subprocess, sys, os, json, time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scenarios_dir = os.path.join(PROJECT, "data", "scenarios")
output_dir = os.path.join(PROJECT, "outputs", "experiments")
os.makedirs(output_dir, exist_ok=True)

seeds = [42, 43, 44, 45, 46]
scenarios = sorted([f for f in os.listdir(scenarios_dir) if f.endswith(".json")])

all_results = []
total = len(scenarios) * len(seeds)
count = 0

for scenario_file in scenarios:
    scenario_path = os.path.join(scenarios_dir, scenario_file)
    for seed in seeds:
        count += 1
        t0 = time.time()
        proc = subprocess.Popen(
            [sys.executable, os.path.join(PROJECT, "scripts", "_run_single.py"),
             scenario_path, str(seed), output_dir],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=180)
        elapsed = time.time() - t0

        result_file = os.path.join(output_dir, f"{scenario_file.replace('.json','')}_seed{seed}.json")
        if os.path.exists(result_file):
            with open(result_file) as f:
                d = json.load(f)
            all_results.append(d)
            print(f"[{count}/{total}] {scenario_file} s{seed}: tasks={d['num_tasks']} makespan={d['makespan']:.1f} success={d['task_success_rate']:.0%} optimal={d['optimal_makespan']:.1f} ({elapsed:.0f}s)", flush=True)
        else:
            error_msg = stderr.decode()[-200:] if stderr else f"RC={proc.returncode}"
            all_results.append({"scenario": scenario_file, "seed": seed, "error": error_msg})
            print(f"[{count}/{total}] {scenario_file} s{seed}: FAILED RC={proc.returncode}", flush=True)
        time.sleep(1)

summary = {
    "total_experiments": len(all_results),
    "successful": sum(1 for r in all_results if "error" not in r),
    "failed": sum(1 for r in all_results if "error" in r),
    "seeds": seeds,
    "scenarios": scenarios,
    "results": all_results,
}
with open(os.path.join(output_dir, "experiment_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nDONE: {summary['successful']}/{summary['total_experiments']} experiments completed")
