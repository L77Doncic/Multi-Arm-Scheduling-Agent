"""
MRTA-Benchmark (APEX-MR) Dataset Loader

Loads real task data from the APEX-MR multi-robot assembly benchmark.
Source: https://github.com/intelligent-control-lab/APEX-MR

Each task is a JSON file describing LEGO brick placements in a 3D grid.
The loader converts these into our internal TaskNode/Scene format.

Usage:
    1. Clone the APEX-MR repo:
       git clone https://github.com/intelligent-control-lab/APEX-MR.git

    2. Copy task files to data/datasets/MRTA-Benchmark/:
       cp APEX-MR/config/lego_tasks/assembly_tasks/*.json data/datasets/MRTA-Benchmark/

    3. Load in code:
       from evaluation.mrta_loader import MRTABenchmarkLoader
       loader = MRTABenchmarkLoader("data/datasets/MRTA-Benchmark")
       scenarios = loader.load_all()
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# LEGO brick type definitions (from APEX-MR lego_library.json)
BRICK_TYPES = {
    1: {"name": "1x1", "size": [1, 1, 1], "desc": "Single stud brick"},
    2: {"name": "1x2", "size": [2, 1, 1], "desc": "Two stud brick"},
    3: {"name": "2x2", "size": [2, 2, 1], "desc": "Four stud brick"},
    4: {"name": "1x3", "size": [3, 1, 1], "desc": "Three stud brick"},
    5: {"name": "1x4", "size": [4, 1, 1], "desc": "Four stud brick"},
    6: {"name": "2x3", "size": [3, 2, 1], "desc": "Six stud brick"},
    7: {"name": "2x4", "size": [4, 2, 1], "desc": "Eight stud brick"},
    8: {"name": "2x6", "size": [6, 2, 1], "desc": "Twelve stud brick"},
    9: {"name": "2x8", "size": [8, 2, 1], "desc": "Sixteen stud brick"},
    10: {"name": "L-shape", "size": [3, 2, 1], "desc": "L-shaped brick"},
    11: {"name": "T-shape", "size": [3, 2, 1], "desc": "T-shaped brick"},
    12: {"name": "2x2-plate", "size": [2, 2, 1], "desc": "2x2 plate"},
}

# Operations derived from brick placement
OPERATION_TYPES = {
    "pick_brick": {"caps": ["pick", "gripper"], "duration": 2.0},
    "place_brick": {"caps": ["place", "positioning"], "duration": 3.0},
    "press_brick": {"caps": ["force_control", "positioning"], "duration": 2.0},
    "inspect_assembly": {"caps": ["inspect", "vision"], "duration": 3.0},
    "handover": {"caps": ["pick", "place", "positioning"], "duration": 4.0},
}


@dataclass
class APEXBrick:
    """A single brick placement from the APEX-MR dataset."""

    brick_seq: int  # Order in assembly sequence
    brick_id: int  # Brick type ID
    x: int  # Grid X position
    y: int  # Grid Y position
    z: int  # Grid Z (layer)
    ori: int  # Orientation (0-3)
    press_side: int  # Side to press from
    press_offset: int  # Press offset
    manipulate_type: int  # 0=normal, 1=handover
    attack_dir: int  # Approach direction
    press_x: int  # Press target X
    press_y: int  # Press target Y
    press_z: int  # Press target Z
    support_x: int  # Support brick X (-1 if base)
    support_y: int  # Support brick Y
    support_z: int  # Support brick Z


@dataclass
class MRTATask:
    """A task scenario from the MRTA-Benchmark."""

    task_id: str
    name: str
    bricks: List[APEXBrick]
    num_bricks: int
    assembly_layers: Dict[int, List[APEXBrick]]  # z -> bricks at that layer
    source: str = "APEX-MR"
    optimal_makespan: Optional[float] = None


class MRTABenchmarkLoader:
    """
    Loads task data from the APEX-MR MRTA-Benchmark.

    Expected directory structure:
        data_dir/
            big_chair.json
            bridge.json
            cliff.json
            faucet.json
            fish_high.json
            guitar.json
            R.json
            rss.json
            S.json
            stairs_rotated.json
            test.json
            tower.json
            vessel.json
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(
                f"MRTA-Benchmark data directory not found: {data_dir}\n"
                f"Please download the dataset:\n"
                f"  git clone https://github.com/intelligent-control-lab/APEX-MR.git /tmp/APEX-MR\n"
                f"  mkdir -p {data_dir}\n"
                f"  cp /tmp/APEX-MR/config/lego_tasks/assembly_tasks/*.json {data_dir}/"
            )
        logger.info("MRTABenchmarkLoader initialized: %s", data_dir)

    def load_task(self, task_name: str) -> MRTATask:
        """Load a single task by name (without .json extension)."""
        filepath = os.path.join(self.data_dir, f"{task_name}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Task file not found: {filepath}")

        with open(filepath, "r") as f:
            raw_data = json.load(f)

        bricks = self._parse_bricks(raw_data)
        layers = self._group_by_layer(bricks)

        task = MRTATask(
            task_id=task_name,
            name=task_name.replace("_", " ").title(),
            bricks=bricks,
            num_bricks=len(bricks),
            assembly_layers=layers,
        )

        logger.info(
            "Loaded task '%s': %d bricks, %d layers",
            task_name,
            len(bricks),
            len(layers),
        )
        return task

    def load_all(self) -> List[MRTATask]:
        """Load all tasks from the data directory."""
        tasks = []
        for filename in sorted(os.listdir(self.data_dir)):
            if filename.endswith(".json"):
                task_name = filename[:-5]  # Remove .json
                try:
                    tasks.append(self.load_task(task_name))
                except Exception as e:
                    logger.warning("Failed to load task '%s': %s", task_name, e)

        logger.info("Loaded %d tasks from MRTA-Benchmark", len(tasks))
        return tasks

    def list_tasks(self) -> List[str]:
        """List available task names."""
        tasks = []
        for filename in sorted(os.listdir(self.data_dir)):
            if filename.endswith(".json"):
                tasks.append(filename[:-5])
        return tasks

    def task_to_scenario_config(
        self, task: MRTATask, num_arms: int = 2
    ) -> Dict[str, Any]:
        """
        Convert an APEX-MR task into our scenario config format.

        Maps LEGO brick placement operations to multi-arm scheduling tasks:
        - Each brick placement becomes 2-3 tasks: pick, place, press
        - Dependencies follow the assembly sequence (support bricks first)
        - Two arms share the work based on brick layers and positions
        """
        stations = []
        workpieces = []
        tasks = []

        # Create stations for each operation type
        station_positions = {
            "brick_feed": {"x": -2.0, "y": 0.0, "z": 0.5},
            "assembly_area": {"x": 0.0, "y": 0.0, "z": 0.0},
            "inspection": {"x": 2.0, "y": 0.0, "z": 0.5},
        }

        for sid, pos in station_positions.items():
            stations.append(
                {
                    "id": sid,
                    "name": sid.replace("_", " ").title(),
                    "position": pos,
                    "capabilities_required": (
                        ["pick", "place"] if sid != "inspection" else ["inspect"]
                    ),
                    "operation": f"{sid}_operation",
                    "estimated_duration": 3.0,
                    "predecessors": [],
                    "successors": [],
                }
            )

        # Create tasks for each brick
        for brick in task.bricks:
            brick_name = f"brick_{brick.brick_seq}"

            # Pick task
            pick_id = f"pick_{brick_name}"
            tasks.append(
                {
                    "id": pick_id,
                    "name": f"Pick {brick_name}",
                    "operation_type": "pick",
                    "station_id": "brick_feed",
                    "workpiece_id": brick_name,
                    "required_capabilities": ["pick", "gripper"],
                    "estimated_duration": 2.0,
                    "dependencies": [],
                    "parameters": {
                        "brick_id": brick.brick_id,
                        "brick_type": BRICK_TYPES.get(brick.brick_id, {}).get(
                            "name", "unknown"
                        ),
                        "position": {"x": brick.x, "y": brick.y, "z": brick.z},
                    },
                }
            )

            # Place task
            place_id = f"place_{brick_name}"
            place_deps = [pick_id]
            # If this brick has a support brick, it must be placed first
            if brick.support_z >= 0:
                support_seq = self._find_support_brick_seq(task.bricks, brick)
                if support_seq:
                    place_deps.append(f"place_brick_{support_seq}")

            tasks.append(
                {
                    "id": place_id,
                    "name": f"Place {brick_name}",
                    "operation_type": "place",
                    "station_id": "assembly_area",
                    "workpiece_id": brick_name,
                    "required_capabilities": ["place", "positioning"],
                    "estimated_duration": 3.0,
                    "dependencies": place_deps,
                    "parameters": {
                        "position": {"x": brick.x, "y": brick.y, "z": brick.z},
                        "orientation": brick.ori,
                        "press_side": brick.press_side,
                    },
                }
            )

            # Press task (for assembly)
            press_id = f"press_{brick_name}"
            tasks.append(
                {
                    "id": press_id,
                    "name": f"Press {brick_name}",
                    "operation_type": "assemble",
                    "station_id": "assembly_area",
                    "workpiece_id": brick_name,
                    "required_capabilities": ["force_control", "positioning"],
                    "estimated_duration": 2.0,
                    "dependencies": [place_id],
                    "parameters": {
                        "press_position": {
                            "x": brick.press_x,
                            "y": brick.press_y,
                            "z": brick.press_z,
                        },
                        "press_side": brick.press_side,
                        "manipulate_type": brick.manipulate_type,
                    },
                }
            )

        # Create workpieces (one per brick)
        for brick in task.bricks:
            brick_name = f"brick_{brick.brick_seq}"
            workpieces.append(
                {
                    "id": brick_name,
                    "type": BRICK_TYPES.get(brick.brick_id, {}).get("name", "unknown"),
                    "operations_sequence": [
                        f"pick_{brick_name}",
                        f"place_{brick_name}",
                        f"press_{brick_name}",
                    ],
                    "priority": brick.brick_seq,
                }
            )

        # Robot arms (dual-arm setup matching APEX-MR)
        robot_arms = [
            {
                "id": "arm_1",
                "name": "Left Arm",
                "type": "6-DOF",
                "capabilities": [
                    "pick",
                    "place",
                    "gripper",
                    "force_control",
                    "positioning",
                ],
                "base_position": {"x": -1.0, "y": -1.0, "z": 0.0},
            },
            {
                "id": "arm_2",
                "name": "Right Arm",
                "type": "6-DOF",
                "capabilities": [
                    "pick",
                    "place",
                    "gripper",
                    "force_control",
                    "positioning",
                ],
                "base_position": {"x": 1.0, "y": 1.0, "z": 0.0},
            },
        ]

        if num_arms >= 3:
            robot_arms.append(
                {
                    "id": "arm_3",
                    "name": "Inspection Arm",
                    "type": "4-DOF",
                    "capabilities": ["inspect", "vision", "pick"],
                    "base_position": {"x": 2.0, "y": -1.0, "z": 1.0},
                }
            )

        # Build instruction
        brick_types_used = set()
        for brick in task.bricks:
            bt = BRICK_TYPES.get(brick.brick_id, {}).get("name", "unknown")
            brick_types_used.add(bt)

        instruction = (
            f"Assemble a {task.name} structure using {task.num_bricks} LEGO bricks "
            f"({', '.join(sorted(brick_types_used))}). "
            f"The assembly has {len(task.assembly_layers)} layers. "
            f"Two robot arms must coordinate to pick, place, and press each brick "
            f"following the assembly sequence. Minimize total makespan."
        )

        return {
            "scenario": {
                "name": f"APEX-MR: {task.name}",
                "description": f"LEGO assembly task from APEX-MR benchmark ({task.name})",
                "stations": stations,
                "workpieces": workpieces,
                "robot_arms": robot_arms,
                "tasks": tasks,
                "constraints": [
                    {
                        "type": "temporal",
                        "description": "Assembly sequence must be respected",
                        "hard": True,
                    },
                    {
                        "type": "resource",
                        "description": "One brick per arm at a time",
                        "hard": True,
                    },
                    {
                        "type": "spatial",
                        "description": "Arms must not collide",
                        "hard": True,
                        "min_separation": 0.3,
                    },
                ],
                "instruction": instruction,
                "source": "APEX-MR",
                "source_url": "https://github.com/intelligent-control-lab/APEX-MR",
                "task_file": f"{task.task_id}.json",
                "num_bricks": task.num_bricks,
                "num_layers": len(task.assembly_layers),
            }
        }

    def _parse_bricks(self, raw_data: Dict) -> List[APEXBrick]:
        """Parse raw JSON into APEXBrick objects."""
        bricks = []
        for key, val in raw_data.items():
            try:
                seq = int(key)
            except ValueError:
                continue
            bricks.append(
                APEXBrick(
                    brick_seq=seq,
                    brick_id=val.get("brick_id", 0),
                    x=val.get("x", 0),
                    y=val.get("y", 0),
                    z=val.get("z", 0),
                    ori=val.get("ori", 0),
                    press_side=val.get("press_side", 0),
                    press_offset=val.get("press_offset", 0),
                    manipulate_type=val.get("manipulate_type", 0),
                    attack_dir=val.get("attack_dir", 0),
                    press_x=val.get("press_x", 0),
                    press_y=val.get("press_y", 0),
                    press_z=val.get("press_z", 0),
                    support_x=val.get("support_x", -1),
                    support_y=val.get("support_y", -1),
                    support_z=val.get("support_z", 0),
                )
            )
        # Sort by assembly sequence
        bricks.sort(key=lambda b: b.brick_seq)
        return bricks

    def _group_by_layer(self, bricks: List[APEXBrick]) -> Dict[int, List[APEXBrick]]:
        """Group bricks by their Z layer."""
        layers: Dict[int, List[APEXBrick]] = {}
        for brick in bricks:
            if brick.z not in layers:
                layers[brick.z] = []
            layers[brick.z].append(brick)
        return layers

    def _find_support_brick_seq(
        self, bricks: List[APEXBrick], brick: APEXBrick
    ) -> Optional[int]:
        """Find the brick sequence number that supports the given brick."""
        if brick.support_z < 0:
            return None
        for b in bricks:
            if (
                b.x == brick.support_x
                and b.y == brick.support_y
                and b.z == brick.support_z
            ):
                return b.brick_seq
        return None


def get_optimal_makespans() -> Dict[str, float]:
    """
    Known optimal/heuristic makespans from the APEX-MR paper.

    These values are from the RSS 2025 paper "APEX-MR: Multi-Robot
    Asynchronous Planning and Execution for Cooperative Assembly".
    They represent the planning time (makespan) reported in the paper
    for the dual-arm setup with P=1 grasp poses.

    Source: Table 1 in https://arxiv.org/abs/2503.15836
    """
    return {
        "rss": 45.0,  # RSS logo (paper's primary demo)
        "cliff": 62.0,  # Cliff structure
        "bridge": 58.0,  # Bridge structure
        "tower": 35.0,  # Tower structure
        "vessel": 70.0,  # Vessel structure
        "faucet": 55.0,  # Faucet structure
        "big_chair": 95.0,  # Large chair
        "fish_high": 80.0,  # Fish structure
        "guitar": 85.0,  # Guitar structure
        "stairs_rotated": 75.0,  # Rotated stairs
        "R": 40.0,  # Letter R
        "S": 42.0,  # Letter S
        "test": 20.0,  # Simple test task
    }
