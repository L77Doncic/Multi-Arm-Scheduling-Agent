"""
Task Planner Module

Uses LLM to decompose natural language instructions into structured task plans
with dependency graphs, resource requirements, and scheduling constraints.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    """A node in the task dependency graph."""

    id: str
    name: str
    description: str
    operation_type: str
    station_id: Optional[str] = None
    workpiece_id: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class TaskPlan:
    """Complete task plan with dependency graph."""

    plan_id: str
    instruction: str
    tasks: List[TaskNode]
    dependency_graph: Dict[str, List[str]]
    estimated_makespan: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_execution_order(self) -> List[List[str]]:
        """Return tasks grouped by execution level (topological sort)."""
        in_degree: Dict[str, int] = {t.id: 0 for t in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[task.id] += 1

        levels: List[List[str]] = []
        remaining = set(in_degree.keys())

        while remaining:
            # Find all nodes with zero in-degree among remaining
            level = [n for n in remaining if in_degree[n] == 0]
            if not level:
                # Circular dependency - break it
                level = [min(remaining)]
                logger.warning("Circular dependency detected, breaking at %s", level[0])

            levels.append(level)
            for node in level:
                remaining.discard(node)
                # Reduce in-degree for dependents
                for task in self.tasks:
                    if node in task.dependencies and task.id in remaining:
                        in_degree[task.id] -= 1

        return levels

    def get_task_by_id(self, task_id: str) -> Optional[TaskNode]:
        """Look up a task by ID."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None


class TaskPlanner:
    """
    LLM-powered task planner that decomposes natural language instructions
    into structured task plans.
    """

    def __init__(self, config: Dict[str, Any], llm_client=None):
        self.config = config
        self.llm_client = llm_client
        self.plan_counter = 0
        logger.info("TaskPlanner initialized")

    def create_plan(
        self, instruction: str, scene_config: Optional[Dict] = None
    ) -> TaskPlan:
        """
        Create a task plan from a natural language instruction.

        Args:
            instruction: Natural language task description.
            scene_config: Optional scene configuration with stations, workpieces, arms.

        Returns:
            TaskPlan with structured tasks and dependency graph.
        """
        self.plan_counter += 1
        plan_id = f"plan_{self.plan_counter:04d}"
        logger.info("Creating plan %s for instruction: %s", plan_id, instruction[:80])

        if self.llm_client:
            plan = self._plan_with_llm(plan_id, instruction, scene_config)
        else:
            plan = self._plan_with_heuristics(plan_id, instruction, scene_config)

        logger.info(
            "Plan %s created with %d tasks, est. makespan=%.1f",
            plan_id,
            len(plan.tasks),
            plan.estimated_makespan,
        )
        return plan

    def _plan_with_llm(
        self, plan_id: str, instruction: str, scene_config: Optional[Dict]
    ) -> TaskPlan:
        """Use LLM to create a task plan."""
        from .prompts.task_decomposition import task_decompose_prompt

        prompt = task_decompose_prompt(instruction, scene_config or {})
        try:
            response = self.llm_client.generate_structured(
                prompt, schema=self._get_plan_schema()
            )
            return self._parse_plan_response(plan_id, instruction, response)
        except Exception as e:
            logger.warning("LLM planning failed (%s), falling back to heuristics", e)
            return self._plan_with_heuristics(plan_id, instruction, scene_config)

    def _plan_with_heuristics(
        self, plan_id: str, instruction: str, scene_config: Optional[Dict]
    ) -> TaskPlan:
        """Create a task plan using heuristic rules (no LLM)."""
        tasks: List[TaskNode] = []
        instruction_lower = instruction.lower()

        # Extract stations and workpieces from scene config
        stations = (scene_config or {}).get("stations", [])
        workpieces = (scene_config or {}).get("workpieces", [])
        arms = (scene_config or {}).get("robot_arms", [])

        if stations and workpieces:
            tasks = self._plan_from_scene(stations, workpieces)
        else:
            tasks = self._plan_from_instruction(instruction_lower)

        # Build dependency graph
        dep_graph: Dict[str, List[str]] = {}
        for t in tasks:
            dep_graph[t.id] = list(t.dependencies)

        # Estimate makespan via critical path
        est_makespan = self._estimate_makespan(tasks)

        return TaskPlan(
            plan_id=plan_id,
            instruction=instruction,
            tasks=tasks,
            dependency_graph=dep_graph,
            estimated_makespan=est_makespan,
            metadata={"method": "heuristic", "num_stations": len(stations)},
        )

    def _plan_from_scene(
        self, stations: List[Dict], workpieces: List[Dict]
    ) -> List[TaskNode]:
        """
        Generate tasks from scene configuration with parallel opportunities.

        Key design: Tasks within the same workpiece are sequential (you can't
        assemble before picking), but tasks across DIFFERENT workpieces can
        run in parallel if they use different stations/robots.
        """
        tasks: List[TaskNode] = []
        task_counter = 0

        for wp in workpieces:
            wp_id = wp.get("id", "wp")
            op_sequence = wp.get("operations_sequence", [])
            prev_task_id: Optional[str] = None

            for station_id in op_sequence:
                task_counter += 1
                task_id = f"t_{task_counter:03d}"

                # Find station config
                station = next((s for s in stations if s["id"] == station_id), None)
                if not station:
                    continue

                op_name = station.get("operation", station_id)
                caps = station.get("capabilities_required", [])
                duration = station.get("estimated_duration", 3.0)

                # Dependencies: only within the same workpiece (sequential)
                # Tasks across different workpieces can run in parallel
                deps = [prev_task_id] if prev_task_id else []

                task = TaskNode(
                    id=task_id,
                    name=f"{op_name}_{wp_id}",
                    description=f"Execute {op_name} for {wp_id} at {station_id}",
                    operation_type=op_name,
                    station_id=station_id,
                    workpiece_id=wp_id,
                    required_capabilities=caps,
                    estimated_duration=duration,
                    dependencies=deps,
                    priority=wp.get("priority", 1),
                )
                tasks.append(task)
                prev_task_id = task_id

        logger.info(
            "Generated %d tasks with parallel opportunities across %d workpieces",
            len(tasks), len(workpieces),
        )
        return tasks

    def _plan_from_instruction(self, instruction: str) -> List[TaskNode]:
        """Generate tasks from instruction text using pattern matching."""
        tasks: List[TaskNode] = []
        task_counter = 0

        # Operation patterns to detect
        patterns = {
            "pick": (["pick", "grab", "grasp", "take"], 2.0, ["pick"]),
            "place": (["place", "put", "set", "drop"], 2.0, ["place"]),
            "move": (["move", "transfer", "transport", "carry"], 3.0, ["move"]),
            "assemble": (
                ["assemble", "connect", "attach", "join"],
                8.0,
                ["assemble", "gripper"],
            ),
            "inspect": (["inspect", "check", "verify", "examine"], 5.0, ["inspect"]),
            "tighten": (["tighten", "secure", "bolt", "screw"], 3.0, ["tighten"]),
            "weld": (["weld", "solder", "bond"], 6.0, ["weld"]),
            "package": (["package", "pack", "box", "output"], 3.0, ["pick", "place"]),
        }

        prev_task_id: Optional[str] = None
        for op_type, (keywords, duration, caps) in patterns.items():
            if any(kw in instruction for kw in keywords):
                task_counter += 1
                task_id = f"t_{task_counter:03d}"
                deps = [prev_task_id] if prev_task_id else []

                tasks.append(
                    TaskNode(
                        id=task_id,
                        name=f"{op_type}_operation",
                        description=f"Execute {op_type} operation",
                        operation_type=op_type,
                        required_capabilities=caps,
                        estimated_duration=duration,
                        dependencies=deps,
                    )
                )
                prev_task_id = task_id

        return tasks

    def _estimate_makespan(self, tasks: List[TaskNode]) -> float:
        """Estimate makespan via critical path analysis."""
        if not tasks:
            return 0.0

        # Build earliest start times
        task_map = {t.id: t for t in tasks}
        earliest_end: Dict[str, float] = {}

        def get_earliest_end(task_id: str) -> float:
            if task_id in earliest_end:
                return earliest_end[task_id]
            task = task_map.get(task_id)
            if not task:
                return 0.0
            if not task.dependencies:
                earliest_end[task_id] = task.estimated_duration
            else:
                max_dep_end = (
                    max(
                        get_earliest_end(dep)
                        for dep in task.dependencies
                        if dep in task_map
                    )
                    if task.dependencies
                    else 0.0
                )
                earliest_end[task_id] = max_dep_end + task.estimated_duration
            return earliest_end[task_id]

        for t in tasks:
            get_earliest_end(t.id)

        return max(earliest_end.values()) if earliest_end else 0.0

    def _get_plan_schema(self) -> Dict[str, Any]:
        """JSON schema for LLM plan output."""
        return {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "operation_type": {"type": "string"},
                            "required_capabilities": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "estimated_duration": {"type": "number"},
                            "dependencies": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "station_id": {"type": "string"},
                            "workpiece_id": {"type": "string"},
                        },
                        "required": ["id", "name", "operation_type"],
                    },
                }
            },
            "required": ["tasks"],
        }

    def _parse_plan_response(
        self, plan_id: str, instruction: str, response: Dict
    ) -> TaskPlan:
        """Parse LLM response into a TaskPlan."""
        tasks = []
        for t in response.get("tasks", []):
            tasks.append(
                TaskNode(
                    id=t["id"],
                    name=t.get("name", t["id"]),
                    description=t.get("description", ""),
                    operation_type=t.get("operation_type", "unknown"),
                    station_id=t.get("station_id"),
                    workpiece_id=t.get("workpiece_id"),
                    required_capabilities=t.get("required_capabilities", []),
                    estimated_duration=t.get("estimated_duration", 3.0),
                    dependencies=t.get("dependencies", []),
                )
            )

        dep_graph = {t.id: list(t.dependencies) for t in tasks}
        est_makespan = self._estimate_makespan(tasks)

        return TaskPlan(
            plan_id=plan_id,
            instruction=instruction,
            tasks=tasks,
            dependency_graph=dep_graph,
            estimated_makespan=est_makespan,
            metadata={"method": "llm"},
        )
