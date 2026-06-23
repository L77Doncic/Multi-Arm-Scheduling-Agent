#!/usr/bin/env python3
"""
Run experiments with Isaac Sim and capture simulation video.

Usage:
    python scripts/run_isaac_sim_experiment.py --scenario data/scenarios/assembly_line_4station.yaml
    python scripts/run_isaac_sim_experiment.py --scenario data/scenarios/complex_assembly.yaml
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def setup_isaac_env():
    """Set up environment variables for Isaac Sim."""
    os.environ["ACCEPT_EULA"] = "Y"
    os.environ["VK_ICD_FILENAMES"] = "/tmp/vulkan_icd/nvidia_icd.json"

    # Find and add USD libs to LD_LIBRARY_PATH
    ov_data = Path.home() / ".local/share/ov/data/exts/v2"
    for d in ov_data.iterdir():
        if d.name.startswith("omni.usd.libs"):
            usd_libs = str(d / "bin")
            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if usd_libs not in ld_path:
                os.environ["LD_LIBRARY_PATH"] = f"{usd_libs}:{ld_path}"
            break


def run_simulation_with_video(scenario_path: str, output_dir: str):
    """Run simulation with Isaac Sim and capture video frames."""
    import yaml

    setup_isaac_env()

    # Load scenario
    with open(scenario_path) as f:
        scenario = yaml.safe_load(f)["scenario"]

    instruction = scenario.get("instruction", "Execute assembly tasks")
    scene_config = scenario

    print(f"Scenario: {scenario.get('name', 'unknown')}")
    print(f"Instruction: {instruction[:80]}...")

    # Create SimulationApp
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True})
    print("SimulationApp created")

    # Now import Isaac Sim modules
    from omni.isaac.core import World
    from omni.isaac.core.objects import DynamicCuboid
    from pxr import UsdGeom
    import omni.usd

    # Create world
    world = World(stage_units_in_meters=1.0)

    # Get stage and create scene
    stage = omni.usd.get_context().get_stage()
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Robots")
    UsdGeom.Xform.Define(stage, "/World/Objects")

    # Load robot arms
    for arm_cfg in scene_config.get("robot_arms", []):
        pos = arm_cfg.get("base_position") or arm_cfg.get("position", {})
        prim_path = f"/World/Robots/{arm_cfg['id']}"
        xform = UsdGeom.Xform.Define(stage, prim_path)
        xform.AddTranslateOp().Set(
            (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))
        )

    # Load workpieces as cuboids
    for wp_cfg in scene_config.get("workpieces", []):
        pos = wp_cfg.get("initial_position", {})
        world.scene.add(
            DynamicCuboid(
                prim_path=f"/World/Objects/{wp_cfg['id']}",
                name=wp_cfg["id"],
                position=[pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)],
                scale=[0.05, 0.05, 0.05],
            )
        )

    world.reset()
    print("Scene loaded into Isaac Sim")

    # Set up video capture using Omni Replicator
    frames = []
    try:
        import omni.replicator.core as rep

        # Create camera
        camera = rep.create.camera(
            position=(8, 8, 8), look_at=(3, 0, 0.5)
        )
        render_product = rep.create.render_product(camera, resolution=(1920, 1080))

        # Attach RGB annotator
        annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        annotator.attach(render_product)

        rep.orchestrator.run()
        print("Video capture setup complete")
        has_replicator = True
    except Exception as e:
        print(f"Replicator not available: {e}")
        has_replicator = False

    # Execute tasks using the agent
    from agent.core import SchedulingAgent

    config = yaml.safe_load(open(PROJECT_ROOT / "configs" / "agent_config.yaml"))
    config.pop("llm", None)  # Use heuristic mode

    # Update robot arms config
    config["robot_arms"] = scene_config.get("robot_arms", config.get("robot_arms", []))

    agent = SchedulingAgent(config)

    # Run scheduling
    print("Executing scheduling pipeline...")
    start_time = time.time()

    # Create a simulation adapter that uses the real Isaac Sim world
    from simulation.isaac_sim import IsaacSimInterface

    sim = IsaacSimInterface.__new__(IsaacSimInterface)
    sim._app = app
    sim._world = world
    sim._IsaacWorld = World
    sim._initialized = True
    sim._scene_loaded = True
    sim._use_mock = False
    sim._mock = None

    result = agent.execute_scheduling(
        instruction=instruction, scene_config=scene_config, simulation=sim
    )

    elapsed = time.time() - start_time

    # Capture frames after execution
    if has_replicator:
        print("Capturing video frames...")
        for i in range(300):  # 10 seconds at 30fps
            try:
                rep.orchestrator.step()
                data = annotator.get_data()
                if data is not None:
                    frames.append(data)
            except Exception:
                break

    # Print results
    print(f"\n{'='*60}")
    print(f"ISAAC SIM EXPERIMENT RESULTS")
    print(f"{'='*60}")
    print(f"Scenario: {scenario.get('name', 'unknown')}")
    print(f"Tasks: {len(result.tasks)}")
    print(f"Makespan: {result.makespan:.1f}s")
    print(f"Success Rate: {result.task_success_rate:.0%}")
    print(f"Resource Utilization: {result.resource_utilization:.0%}")
    print(f"Constraint Violations: {result.constraint_violations}")
    print(f"Execution Time: {elapsed:.1f}s")
    print(f"Feedback Adjustments: {len(result.feedback_adjustments)}")
    print(f"Video Frames: {len(frames)}")

    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    import json

    result_data = {
        "scenario": scenario_path,
        "backend": "isaac_sim",
        "tasks": len(result.tasks),
        "makespan": result.makespan,
        "task_success_rate": result.task_success_rate,
        "resource_utilization": result.resource_utilization,
        "constraint_violations": result.constraint_violations,
        "execution_time": elapsed,
        "feedback_adjustments": len(result.feedback_adjustments),
        "execution_log": result.execution_log,
        "generated_codes_count": len(result.generated_codes),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    result_file = output_path / f"isaac_sim_{scenario.get('name', 'unknown').replace(' ', '_').lower()}.json"
    with open(result_file, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"Results saved to {result_file}")

    # Save video
    if frames:
        video_file = output_path / f"simulation_{scenario.get('name', 'unknown').replace(' ', '_').lower()}.mp4"
        save_video(frames, str(video_file))
        print(f"Video saved to {video_file}")

    # Cleanup
    world.stop()
    world.clear()
    app.close()

    return result_data


def save_video(frames, output_path):
    """Save frames as MP4 video using OpenCV or PIL."""
    try:
        import cv2
        import numpy as np

        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, 30.0, (w, h))
        for frame in frames:
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            elif len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame)
        out.release()
        print(f"Video saved with OpenCV: {output_path}")
    except ImportError:
        # Fallback: save frames as PNGs and use ffmpeg
        import tempfile

        tmpdir = tempfile.mkdtemp()
        for i, frame in enumerate(frames):
            try:
                from PIL import Image

                img = Image.fromarray(frame)
                img.save(f"{tmpdir}/frame_{i:04d}.png")
            except Exception:
                pass

        # Use ffmpeg to create video
        os.system(
            f"ffmpeg -y -framerate 30 -i {tmpdir}/frame_%04d.png "
            f"-c:v libx264 -pix_fmt yuv420p {output_path} 2>/dev/null"
        )
        print(f"Video saved with ffmpeg: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Isaac Sim experiment")
    parser.add_argument(
        "--scenario",
        default="data/scenarios/assembly_line_4station.yaml",
        help="Path to scenario YAML",
    )
    parser.add_argument(
        "--output",
        default="outputs/isaac_sim_experiments",
        help="Output directory",
    )
    args = parser.parse_args()

    run_simulation_with_video(args.scenario, args.output)
