"""
Resource Allocator Module

This module handles the allocation of tasks to robot arms using
greedy capability matching, load balancing, and conflict resolution.
"""

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of resource conflicts."""

    TEMPORAL = "temporal"  # Two tasks scheduled at the same time on one arm
    CAPABILITY = "capability"  # Arm lacks required capability
    RESOURCE = "resource"  # Shared resource contention (e.g. tool, workspace)
    COLLISION = "collision"  # Physical collision risk between arms


@dataclass
class Conflict:
    """Represents a resource allocation conflict."""

    task1_id: str
    task2_id: str
    arm_id: str
    conflict_type: ConflictType


@dataclass
class TaskInfo:
    """Simplified task representation used during allocation."""

    id: str
    required_capabilities: List[str]
    estimated_duration: float
    priority: float = 1.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ArmInfo:
    """Simplified robot arm representation used during allocation."""

    id: str
    capabilities: List[str]
    max_load: float = 1.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    current_load: float = 0.0


class ResourceAllocator:
    """
    Resource allocator for multi-arm scheduling.

    Uses a greedy algorithm that prioritises capability matching as the
    primary scoring criterion, with load-balancing as a secondary
    objective.  Falls back to an LLM-assisted strategy for complex cases
    when the built-in heuristics cannot find a feasible assignment.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise the resource allocator.

        Args:
            config: Configuration dictionary.  Recognised keys:
                * capability_weight   - weight for capability match (default 0.6)
                * workload_weight     - weight for workload balance  (default 0.3)
                * priority_weight     - weight for task priority     (default 0.1)
                * llm_assist_threshold - score below which LLM is consulted (0.3)
                * max_iterations      - max conflict resolution passes (default 10)
        """
        self.config = config
        self.capability_weight: float = config.get("capability_weight", 0.6)
        self.workload_weight: float = config.get("workload_weight", 0.3)
        self.priority_weight: float = config.get("priority_weight", 0.1)
        self.llm_assist_threshold: float = config.get("llm_assist_threshold", 0.3)
        self.max_iterations: int = config.get("max_iterations", 10)

        # Internal state kept between calls for bookkeeping
        self._last_assignment: Dict[str, str] = {}

        logger.info("ResourceAllocator initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_config(self, params: Dict[str, Any]) -> None:
        """
        Accept runtime parameter updates from the feedback loop.

        Args:
            params: Dictionary of parameter name -> new value.
                Supported keys: resource_weight, priority_boost.
        """
        if "resource_weight" in params:
            self.workload_weight = float(params["resource_weight"])
        if "priority_boost" in params:
            self.priority_weight = float(params["priority_boost"])
        logger.info("ResourceAllocator config updated: %s", params)

    def allocate(
        self,
        tasks: List[Any],
        robot_arms: List[Any],
    ) -> Dict[str, str]:
        """
        Allocate tasks to robot arms.

        The method builds lightweight info objects from the inputs, runs
        the greedy matcher, detects and resolves conflicts, and returns
        the final mapping.

        Args:
            tasks: List of task objects.  Each must expose at least
                ``id``, ``required_capabilities``, ``estimated_duration``,
                ``priority`` (optional), and ``dependencies`` (optional).
            robot_arms: List of robot-arm objects.  Each must expose at
                least ``id``, ``capabilities``, and ``max_load``
                (optional).

        Returns:
            Dictionary mapping ``task.id`` -> ``arm.id``.
        """
        logger.info("Allocating %d tasks across %d arms", len(tasks), len(robot_arms))

        task_infos = self._to_task_infos(tasks)
        arm_infos = self._to_arm_infos(robot_arms)

        # Greedy initial assignment
        assignment = self._greedy_assign(task_infos, arm_infos)
        self._last_assignment = dict(assignment)  # Update before conflict resolution

        # Iteratively detect and resolve conflicts
        for iteration in range(self.max_iterations):
            conflicts = self._detect_conflicts(assignment, task_infos, arm_infos)
            if not conflicts:
                break
            logger.debug(
                "Conflict resolution pass %d: %d conflicts",
                iteration + 1,
                len(conflicts),
            )
            assignment = self.resolve_conflicts(conflicts, task_infos, arm_infos)

        self._last_assignment = dict(assignment)
        logger.info("Allocation complete: %d assignments", len(assignment))
        return assignment

    def resolve_conflicts(
        self,
        conflicts: List[Conflict],
        tasks: List[Any],
        arms: List[Any],
    ) -> Dict[str, str]:
        """
        Resolve detected conflicts by re-assigning conflicting tasks.

        For each conflict the lower-priority task is moved to the
        next-best arm.  If no feasible arm is found the task is left in
        place and a warning is logged.

        Args:
            conflicts: Conflicts detected by ``_detect_conflicts``.
            tasks: Original task list (or TaskInfo list).
            arms: Original arm list (or ArmInfo list).

        Returns:
            Updated assignment dictionary.
        """
        task_infos = (
            self._to_task_infos(tasks)
            if tasks and not isinstance(tasks[0], TaskInfo)
            else tasks
        )
        arm_infos = (
            self._to_arm_infos(arms)
            if arms and not isinstance(arms[0], ArmInfo)
            else arms
        )

        task_map: Dict[str, TaskInfo] = {t.id: t for t in task_infos}
        arm_map: Dict[str, ArmInfo] = {a.id: a for a in arm_infos}

        # Start from the current best assignment
        # Use the passed-in assignment if available, fall back to _last_assignment
        assignment: Dict[str, str] = dict(self._last_assignment)

        for conflict in conflicts:
            # For capability conflicts the task to move is unambiguous
            if conflict.conflict_type == ConflictType.CAPABILITY:
                t1 = task_map.get(conflict.task1_id)
                if t1 is None:
                    continue
                task_to_move = t1
            else:
                # Decide which task to move (the one with lower priority)
                t1 = task_map.get(conflict.task1_id)
                t2 = task_map.get(conflict.task2_id)
                if t1 is None or t2 is None:
                    continue
                task_to_move = t1 if t1.priority <= t2.priority else t2

            # Find the next-best arm for the displaced task
            current_arm_id = assignment.get(task_to_move.id)
            best_arm_id: Optional[str] = None
            best_score = -math.inf
            current_score = -math.inf

            for arm in arm_infos:
                score = self._match_capabilities(task_to_move, arm)
                if arm.id == current_arm_id:
                    current_score = score
                    continue
                if score > best_score:
                    best_score = score
                    best_arm_id = arm.id

            # Only move if the alternative is genuinely better than the
            # current assignment and meets the minimum threshold
            if (
                best_arm_id is not None
                and best_score >= self.llm_assist_threshold
                and best_score > current_score
            ):
                assignment[task_to_move.id] = best_arm_id
                logger.debug(
                    "Moved task %s from arm %s to arm %s (score %.2f)",
                    task_to_move.id,
                    current_arm_id,
                    best_arm_id,
                    best_score,
                )
            else:
                logger.warning(
                    "No suitable alternative arm found for task %s; "
                    "keeping current assignment on arm %s",
                    task_to_move.id,
                    current_arm_id,
                )

        return assignment

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_task_infos(self, tasks: List[Any]) -> List[TaskInfo]:
        """Convert arbitrary task objects to ``TaskInfo`` instances."""
        if tasks and isinstance(tasks[0], TaskInfo):
            return tasks
        infos: List[TaskInfo] = []
        for t in tasks:
            infos.append(
                TaskInfo(
                    id=t.id,
                    required_capabilities=list(getattr(t, "required_capabilities", [])),
                    estimated_duration=float(getattr(t, "estimated_duration", 1.0)),
                    priority=float(getattr(t, "priority", 1.0)),
                    dependencies=list(getattr(t, "dependencies", [])),
                )
            )
        return infos

    def _to_arm_infos(self, arms: List[Any]) -> List[ArmInfo]:
        """Convert arbitrary arm objects to ``ArmInfo`` instances."""
        if arms and isinstance(arms[0], ArmInfo):
            return arms
        infos: List[ArmInfo] = []
        for a in arms:
            pos = getattr(a, "position", (0.0, 0.0, 0.0))
            if not isinstance(pos, tuple):
                pos = tuple(pos)
            infos.append(
                ArmInfo(
                    id=a.id,
                    capabilities=list(getattr(a, "capabilities", [])),
                    max_load=float(getattr(a, "max_load", 1.0)),
                    position=pos,
                    current_load=float(getattr(a, "current_load", 0.0)),
                )
            )
        return infos

    def _greedy_assign(
        self,
        task_infos: List[TaskInfo],
        arm_infos: List[ArmInfo],
    ) -> Dict[str, str]:
        """
        Greedy assignment with parallel opportunity optimization.

        Key improvement: Tasks with no dependency relationship can run
        in parallel on different arms. This increases resource utilization.
        """
        # Sort tasks by priority (highest first)
        sorted_tasks = sorted(task_infos, key=lambda t: t.priority, reverse=True)

        # Build dependency set for quick lookup
        task_deps: Dict[str, set] = {t.id: set(t.dependencies) for t in task_infos}
        task_dependents: Dict[str, set] = defaultdict(set)
        for t in task_infos:
            for dep in t.dependencies:
                task_dependents[dep].add(t.id)

        arm_workload: Dict[str, float] = {a.id: a.current_load for a in arm_infos}
        assignment: Dict[str, str] = {}

        for task in sorted_tasks:
            best_arm_id: Optional[str] = None
            best_score = -math.inf

            for arm in arm_infos:
                cap_score = self._match_capabilities(task, arm)

                # Simulate adding this task to the arm for workload calc
                simulated_assignment = dict(assignment)
                simulated_assignment[task.id] = arm.id
                balance_score = self._calculate_workload_balance(
                    simulated_assignment, task_infos, arm_infos
                )
                priority_score = task.priority / max(
                    max(t.priority for t in task_infos), 1.0
                )

                # Parallel opportunity score: boost score if this task
                # can run in parallel with tasks already on this arm
                parallel_score = self._calculate_parallel_opportunity(
                    task, arm, assignment, task_deps, task_dependents
                )

                # Normalize weights to sum to 1.0
                total_weight = self.capability_weight + self.workload_weight + self.priority_weight + 0.3
                composite = (
                    (self.capability_weight / total_weight) * cap_score
                    + (self.workload_weight / total_weight) * balance_score
                    + (self.priority_weight / total_weight) * priority_score
                    + (0.3 / total_weight) * parallel_score  # 30% weight for parallelism
                )

                if composite > best_score:
                    best_score = composite
                    best_arm_id = arm.id

            if best_arm_id is not None:
                assignment[task.id] = best_arm_id
                arm_workload[best_arm_id] = (
                    arm_workload.get(best_arm_id, 0.0) + task.estimated_duration
                )
            else:
                logger.warning("No arm found for task %s", task.id)

        return assignment

    def _calculate_parallel_opportunity(
        self,
        task: TaskInfo,
        arm: ArmInfo,
        assignment: Dict[str, str],
        task_deps: Dict[str, set],
        task_dependents: Dict[str, set],
    ) -> float:
        """
        Calculate parallel opportunity score for assigning a task to an arm.

        Key insight: Tasks on DIFFERENT arms can run in parallel.
        We want to DISTRIBUTE independent tasks across different arms.

        Returns a score in [0.0, 1.0] where higher means this assignment
        enables more parallel execution.
        """
        # Find tasks already assigned to this arm
        arm_tasks = [tid for tid, aid in assignment.items() if aid == arm.id]

        # Find tasks NOT on this arm (on other arms)
        other_arm_tasks = [tid for tid, aid in assignment.items() if aid != arm.id]

        if not arm_tasks and not other_arm_tasks:
            # First task overall - neutral
            return 0.5

        # Count how many tasks on OTHER arms this task can run in parallel with
        parallel_with_others = 0
        for other_tid in other_arm_tasks:
            # Check if there's no dependency between this task and the other task
            if (other_tid not in task_deps.get(task.id, set()) and
                task.id not in task_deps.get(other_tid, set())):
                parallel_with_others += 1

        # KEY LOGIC: Prefer IDLE arms for parallel execution
        # If this arm has fewer tasks, it's better for parallelism
        arm_load_penalty = len(arm_tasks) / max(len(assignment), 1)

        if parallel_with_others > 0:
            # This task can run in parallel with tasks on other arms
            # Prefer IDLE arms (lower load) for true parallel execution
            base_score = min(1.0, parallel_with_others / max(len(other_arm_tasks), 1))
            # Boost score for idle arms, penalize for busy arms
            return base_score * (1.0 - arm_load_penalty * 0.5)
        else:
            # This task has dependencies with all tasks on other arms
            return 0.2

    def _match_capabilities(self, task: TaskInfo, arm: ArmInfo) -> float:
        """
        Score how well an arm's capabilities match a task's requirements.

        Returns:
            A score in [0.0, 1.0].  1.0 means perfect match (all
            required capabilities are present); 0.0 means no overlap.
        """
        required = set(task.required_capabilities)
        available = set(arm.capabilities)

        if not required:
            # No specific requirements -- any arm will do.
            return 1.0

        matched = required & available
        score = len(matched) / len(required)

        # Penalise if the arm is overloaded relative to its max capacity
        if arm.max_load > 0:
            load_ratio = arm.current_load / arm.max_load
            if load_ratio >= 1.0:
                score *= 0.1  # heavy penalty
            elif load_ratio > 0.8:
                score *= 0.7  # moderate penalty

        return score

    def _calculate_workload_balance(
        self,
        assignment: Dict[str, str],
        task_infos: Optional[List[TaskInfo]] = None,
        arm_infos: Optional[List[ArmInfo]] = None,
    ) -> float:
        """
        Compute a workload-balance metric for an assignment.

        The metric is the complement of the coefficient of variation of
        per-arm total durations: ``1 - CV``.  A perfectly balanced
        assignment returns 1.0; highly skewed assignments approach 0.0.

        Args:
            assignment: Mapping of task_id -> arm_id.
            task_infos: Optional task details (uses stored info if *None*).
            arm_infos: Optional arm details (uses stored info if *None*).

        Returns:
            Balance score in [0.0, 1.0].
        """
        if not assignment:
            return 1.0

        # Build task duration lookup
        if task_infos is not None:
            duration_map: Dict[str, float] = {
                t.id: t.estimated_duration for t in task_infos
            }
        else:
            # Fallback: uniform duration
            duration_map = defaultdict(lambda: 1.0)

        # Sum durations per arm - include ALL arms, not just those with tasks
        arm_totals: Dict[str, float] = defaultdict(float)
        for task_id, arm_id in assignment.items():
            arm_totals[arm_id] += duration_map.get(task_id, 1.0)

        # Add arms with no tasks (load = 0)
        if arm_infos is not None:
            for arm in arm_infos:
                if arm.id not in arm_totals:
                    arm_totals[arm.id] = 0.0

        if len(arm_totals) < 2:
            return 1.0

        values = list(arm_totals.values())
        mean = sum(values) / len(values)
        if mean == 0:
            return 1.0

        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        cv = std / mean

        return max(0.0, 1.0 - cv)

    def _detect_conflicts(
        self,
        assignment: Dict[str, str],
        task_infos: Optional[List[TaskInfo]] = None,
        arm_infos: Optional[List[ArmInfo]] = None,
    ) -> List[Conflict]:
        """
        Detect resource conflicts in an assignment.

        Checks for:
        * **Temporal conflicts** -- two tasks assigned to the same arm
          whose dependency ordering implies overlap.
        * **Capability conflicts** -- a task assigned to an arm that
          lacks a required capability.

        Args:
            assignment: Current task->arm mapping.
            task_infos: Task details.
            arm_infos: Arm details.

        Returns:
            List of ``Conflict`` instances.
        """
        conflicts: List[Conflict] = []

        if task_infos is None or arm_infos is None:
            return conflicts

        task_map: Dict[str, TaskInfo] = {t.id: t for t in task_infos}
        arm_map: Dict[str, ArmInfo] = {a.id: a for a in arm_infos}

        # --- Capability conflicts ---
        for task_id, arm_id in assignment.items():
            task = task_map.get(task_id)
            arm = arm_map.get(arm_id)
            if task is None or arm is None:
                continue
            required = set(task.required_capabilities)
            available = set(arm.capabilities)
            if required and not required.issubset(available):
                conflicts.append(
                    Conflict(
                        task1_id=task_id,
                        task2_id="",
                        arm_id=arm_id,
                        conflict_type=ConflictType.CAPABILITY,
                    )
                )

        # --- Temporal conflicts (overloaded arm) ---
        # A temporal conflict arises when the cumulative load on an arm
        # exceeds its capacity, not simply when multiple tasks share it.
        # Tasks can run sequentially on the same arm without issue.
        arm_tasks: Dict[str, List[str]] = defaultdict(list)
        for task_id, arm_id in assignment.items():
            arm_tasks[arm_id].append(task_id)

        for arm_id, task_ids in arm_tasks.items():
            arm = arm_map.get(arm_id)
            if arm is None:
                continue
            total_duration = sum(
                task_map[tid].estimated_duration for tid in task_ids if tid in task_map
            )
            # If total duration exceeds the arm's effective capacity
            # (derived from max_load), flag pairs for rebalancing
            effective_capacity = arm.max_load * 10.0  # rough scaling
            if total_duration > effective_capacity and len(task_ids) >= 2:
                # Flag the two lowest-priority tasks as conflicting
                sorted_tids = sorted(
                    task_ids,
                    key=lambda tid: task_map[tid].priority if tid in task_map else 0,
                )
                conflicts.append(
                    Conflict(
                        task1_id=sorted_tids[0],
                        task2_id=sorted_tids[1],
                        arm_id=arm_id,
                        conflict_type=ConflictType.TEMPORAL,
                    )
                )

        return conflicts
