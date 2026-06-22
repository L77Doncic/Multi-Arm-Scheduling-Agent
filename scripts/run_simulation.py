#!/usr/bin/env python3
"""
Run Simulation Script

Executes the multi-arm scheduling pipeline on a given scenario:
  1. Load scenario configuration
  2. Initialize the scheduling agent
  3. Run task decomposition + resource allocation + code generation
  4. Execute in simulation (mock or Isaac Sim)
  5. Collect metrics and generate report

Usage:
    python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml
    python scripts/run_simulation.py --scenario data/scenarios/complex_assembly.yaml --sim mock
    python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml --verbose
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def load_scenario(scenario_path: str) -> dict:
    """Load scenario configuration from YAML file."""
    with open(scenario_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_agent_config(config_path: str = "configs/agent_config.yaml") -> dict:
    """Load agent configuration."""
    config_file = PROJECT_ROOT / config_path
    if config_file.exists():
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return {}


def create_simulation(sim_type: str, scene_config: dict):
    """Create simulation interface."""
    if sim_type == "isaac":
        try:
            from simulation.isaac_sim import IsaacSimInterface
            sim = IsaacSimInterface(fallback_to_mock=True)
            sim.initialize()
            sim.load_scene(scene_config)
            return sim
        except ImportError:
            logging.warning("Isaac Sim not available, falling back to mock")

    elif sim_type == "omniverse":
        try:
            from simulation.omniverse import OmniverseInterface
            sim = OmniverseInterface(fallback_to_mock=True)
            sim.initialize()
            sim.load_scene(scene_config)
            return sim
        except ImportError:
            logging.warning("Omniverse not available, falling back to mock")

    elif sim_type == "isaac_lab":
        try:
            from simulation.isaac_lab import IsaacLabInterface
            sim = IsaacLabInterface(fallback_to_mock=True)
            sim.initialize()
            sim.load_scene(scene_config)
            return sim
        except ImportError:
            logging.warning("Isaac Lab not available, falling back to mock")

    from simulation.mock_simulator import MockSimulator

    # Create mock simulator
    sim = MockSimulator(
        failure_probabilities={},  # No failures by default
        time_scale=1.0,  # Real time scale (1.0 = normal speed)
        seed=42,
    )
    sim.initialize()
    sim.load_scene(scene_config)

    return sim


def run_simulation(scenario_path: str, sim_type: str = "mock",
                   verbose: bool = False, output_dir: str = "outputs/results"):
    """Run the full simulation pipeline."""
    setup_logging(verbose)
    logger = logging.getLogger("run_simulation")

    # Load configurations
    logger.info("Loading scenario: %s", scenario_path)
    scenario = load_scenario(scenario_path)
    agent_config = load_agent_config()

    scenario_data = scenario.get('scenario', scenario)
    instruction = scenario_data.get('instruction', 'Execute assembly tasks')
    scene_config = scenario_data

    # Merge robot arms from scenario into agent config
    if 'robot_arms' in scenario_data:
        agent_config['robot_arms'] = scenario_data['robot_arms']

    # Initialize agent
    logger.info("Initializing scheduling agent...")
    from agent.core import SchedulingAgent
    agent = SchedulingAgent(agent_config)

    # Create simulation
    logger.info("Creating simulation (type=%s)...", sim_type)
    sim = create_simulation(sim_type, scene_config)

    # Execute scheduling
    logger.info("Executing scheduling pipeline...")
    start = time.time()
    result = agent.execute_scheduling(
        instruction=instruction,
        scene_config=scene_config,
        simulation=sim
    )
    elapsed = time.time() - start

    # Print results
    print("\n" + "=" * 70)
    print("SIMULATION RESULTS")
    print("=" * 70)
    print(f"Execution ID:    {result.execution_id}")
    print(f"Instruction:     {instruction[:80]}...")
    print(f"Tasks:           {len(result.tasks)}")
    print(f"Makespan:        {result.makespan:.2f}s")
    print(f"Success Rate:    {result.task_success_rate * 100:.1f}%")
    print(f"Resource Util:   {result.resource_utilization * 100:.1f}%")
    print(f"Violations:      {result.constraint_violations}")
    print(f"Wall Clock:      {elapsed:.2f}s")
    print(f"Feedback Adj:    {len(result.feedback_adjustments)}")
    print()

    # Task details
    print("TASK DETAILS:")
    print("-" * 70)
    for task in result.tasks:
        status_icon = "✓" if task.status.value == "completed" else "✗"
        print(f"  {status_icon} {task.id:10s} | {task.name:25s} | "
              f"arm={task.assigned_arm or 'none':8s} | {task.status.value}")
    print()

    # Allocation
    print("RESOURCE ALLOCATION:")
    print("-" * 70)
    for task_id, arm_id in result.allocation.items():
        arm_name = agent.robot_arms[arm_id].name if arm_id in agent.robot_arms else arm_id
        print(f"  {task_id:15s} -> {arm_name} ({arm_id})")
    print()

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"simulation_{result.execution_id}.json")

    output_data = {
        'execution_id': result.execution_id,
        'instruction': instruction,
        'scenario': scenario_path,
        'makespan': result.makespan,
        'task_success_rate': result.task_success_rate,
        'resource_utilization': result.resource_utilization,
        'constraint_violations': result.constraint_violations,
        'num_tasks': len(result.tasks),
        'allocation': result.allocation,
        'execution_log': result.execution_log,
        'feedback_adjustments': [
            {'task_id': a.get('task_id'), 'details': str(a.get('adjustment', ''))}
            for a in result.feedback_adjustments
        ],
        'generated_code_count': len(result.generated_codes),
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    logger.info("Results saved to %s", output_file)

    # Save generated codes
    if result.generated_codes:
        code_dir = os.path.join(output_dir, f"code_{result.execution_id}")
        os.makedirs(code_dir, exist_ok=True)
        for task_id, code in result.generated_codes.items():
            code_file = os.path.join(code_dir, f"{task_id}.py")
            with open(code_file, 'w') as f:
                f.write(code)
        logger.info("Generated code saved to %s", code_dir)

    # Cleanup
    sim.close()

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run multi-arm scheduling simulation"
    )
    parser.add_argument(
        "--scenario", "-s",
        required=True,
        help="Path to scenario YAML file"
    )
    parser.add_argument(
        "--sim",
        default="mock",
        choices=["mock", "isaac", "omniverse", "isaac_lab"],
        help="Simulation backend (default: mock)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs/results",
        help="Output directory (default: outputs/results)"
    )

    args = parser.parse_args()
    run_simulation(args.scenario, args.sim, args.verbose, args.output)


if __name__ == "__main__":
    main()
