#!/usr/bin/env python3
"""Run a single Isaac Sim experiment in a subprocess."""
import os, sys, json, time, yaml, random
import numpy as np

os.environ["ACCEPT_EULA"] = "Y"
os.environ["VK_ICD_FILENAMES"] = "/tmp/vulkan_icd/nvidia_icd.json"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

scenario_path = sys.argv[1]
seed = int(sys.argv[2])
output_dir = sys.argv[3]
os.makedirs(output_dir, exist_ok=True)

random.seed(seed)
np.random.seed(seed)

with open(scenario_path) as f:
    raw = json.load(f)
scenario = raw.get("scenario", raw)

config = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "configs", "agent_config.yaml")))
config["robot_arms"] = scenario["robot_arms"]

from agent.core import SchedulingAgent
from simulation.isaac_sim import IsaacSimInterface

agent = SchedulingAgent(config)
sim = IsaacSimInterface(fallback_to_mock=False)
sim.initialize()
sim.load_scene(scenario)

result = agent.execute_scheduling(
    instruction=scenario.get("instruction", "Execute"),
    scene_config=scenario,
    simulation=sim,
)

# Write result FIRST (before sim.close which may crash)
video_path = None
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
    "video": video_path,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
}
json_path = os.path.join(output_dir, f"{scenario.get('name','unknown')}_seed{seed}.json")
with open(json_path, "w") as f:
    json.dump(exp_result, f, indent=2)

# Save video
frames = sim.get_frames()
if frames:
    try:
        import cv2, subprocess
        h, w = frames[0].shape[:2]
        tmp = os.path.join(output_dir, f"_tmp_{seed}.mp4")
        out = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h))
        for frame in frames:
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR) if frame.shape[2] == 4 else frame
            out.write(bgr)
        out.release()
        video_path = os.path.join(output_dir, f"{scenario.get('name','unknown')}_seed{seed}.mp4")
        subprocess.run(["ffmpeg", "-y", "-r", "30", "-i", tmp, "-vf", "setpts=5*PTS", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", video_path], capture_output=True)
        os.remove(tmp)
    except Exception:
        pass

# Try to close gracefully
try:
    sim.close()
except Exception:
    pass

print(json.dumps(exp_result))
