#!/usr/bin/env python3
"""Run a single experiment in a subprocess.

Uses PhysXOnlySimulator (no Vulkan rendering) for physics computation
with MRTA travel time data.  Produces identical scheduling metrics to
Isaac Sim because task durations are driven by travel time matrices.
"""
import os, sys, json, time, yaml, random
import numpy as np

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
os.chdir(PROJECT_ROOT)  # ensure .env is found by load_dotenv()

scenario_path = sys.argv[1]
seed = int(sys.argv[2])
output_dir = sys.argv[3]
os.makedirs(output_dir, exist_ok=True)

random.seed(seed)
np.random.seed(seed)

with open(scenario_path) as f:
    raw = json.load(f)
scenario = raw.get("scenario", raw)

# Merge mrta_travel_times into scenario if it exists at top level
if "mrta_travel_times" in raw and "mrta_travel_times" not in scenario:
    scenario["mrta_travel_times"] = raw["mrta_travel_times"]

config = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "configs", "agent_config.yaml")))
config["robot_arms"] = scenario["robot_arms"]

from agent.core import SchedulingAgent
from simulation.physx_only import PhysXOnlySimulator

agent = SchedulingAgent(config)
sim = PhysXOnlySimulator()
sim.initialize()
sim.load_scene(scenario)

result = agent.execute_scheduling(
    instruction=scenario.get("instruction", "Execute"),
    scene_config=scenario,
    simulation=sim,
)

# Write result
exp_result = {
    "scenario": scenario.get("name", "unknown"),
    "scenario_file": os.path.basename(scenario_path),
    "seed": seed,
    "optimal_makespan": scenario.get("optimal_schedule", {}).get("makespan", 0),
    "makespan": result.makespan,
    "task_success_rate": result.task_success_rate,
    "resource_utilization": result.resource_utilization,
    "constraint_violations": result.constraint_violations,
    "num_tasks": len(result.tasks),
    "video": None,
    "backend": "physx_only",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
}
json_path = os.path.join(output_dir, f"{scenario.get('name','unknown')}_seed{seed}.json")
with open(json_path, "w") as f:
    json.dump(exp_result, f, indent=2)

print(f"[OK] {scenario.get('name','unknown')} seed={seed} makespan={result.makespan:.1f}s success={result.task_success_rate:.0%}")
