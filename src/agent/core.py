"""
Multi-Arm Scheduling Agent Core Module.

This module implements the core LLM-driven agent that orchestrates the
full scheduling pipeline: task decomposition → resource allocation →
code generation → simulation execution → feedback collection → metrics.

The agent integrates all Harness Engineering components (task decomposer,
resource allocator, result validator, exception handler, feedback loop)
and drives the LLM-powered planner and code generator.
"""

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from harness.exception_handler import RecoveryActionType

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Core data classes
# ------------------------------------------------------------------


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task data class used throughout the system."""

    id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_arm: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    # Extended fields for integration
    operation_type: str = ""
    station_id: Optional[str] = None
    workpiece_id: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    estimated_duration: float = 3.0
    priority: float = 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RobotArm:
    """Robot arm data class."""

    id: str
    name: str
    capabilities: List[str]
    current_task: Optional[str] = None
    is_busy: bool = False
    position: Optional[Dict[str, float]] = None
    max_load: float = 5.0
    current_load: float = 0.0

    # The resource_allocator expects these attribute names
    @property
    def max_payload(self) -> float:
        return self.max_load


@dataclass
class ExecutionResult:
    """Complete result of a scheduling execution."""

    execution_id: str
    instruction: str
    tasks: List[Task]
    allocation: Dict[str, str]
    makespan: float
    task_success_rate: float
    resource_utilization: float
    constraint_violations: int
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    feedback_adjustments: List[Dict[str, Any]] = field(default_factory=list)
    generated_codes: Dict[str, str] = field(default_factory=dict)


# ------------------------------------------------------------------
# Action type mapping (operation_type -> simulation action type)
# ------------------------------------------------------------------

_ACTION_TYPE_MAP: Dict[str, str] = {
    "pick": "pick",
    "pick_workpiece_from_feed": "pick",
    "pick_from_feed": "pick",
    "pick_brick": "pick",
    "place": "place",
    "place_brick": "place",
    "package": "place",
    "package_and_output": "place",
    "output": "place",
    "drop": "place",
    "move": "move",
    "transfer": "move",
    "transport": "move",
    "assemble": "assemble",
    "assemble_components": "assemble",
    "final_assembly": "assemble",
    "join": "assemble",
    "connect": "assemble",
    "press_brick": "assemble",
    "inspect": "inspect",
    "quality_inspection": "inspect",
    "quality_check": "inspect",
    "verify": "inspect",
    "inspect_assembly": "inspect",
    "tighten": "move",  # mock simulator doesn't have tighten; treat as move
    "secure": "move",
    "bolt": "move",
    "weld": "assemble",
    "weld_joints": "assemble",
    "solder": "assemble",
    "prepare": "move",
    "prepare_workpiece": "move",
    "prep": "move",
}


def _map_action_type(operation_type: str) -> str:
    """Map an operation_type to a simulation action type."""
    return _ACTION_TYPE_MAP.get(operation_type, "move")


# ------------------------------------------------------------------
# Scheduling Agent
# ------------------------------------------------------------------


class SchedulingAgent:
    """
    LLM-driven multi-arm scheduling agent.

    Orchestrates the full pipeline:
        1. Task decomposition (LLM or heuristic)
        2. Resource allocation (greedy + conflict resolution)
        3. Code generation (LLM or template)
        4. Simulation execution (mock or Isaac Sim)
        5. Feedback collection & strategy adjustment
        6. Metrics calculation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scheduling agent.

        Args:
            config: Configuration dictionary containing LLM settings,
                   robot arm definitions, harness settings, and task params.
        """
        self.config = config
        self.tasks: Dict[str, Task] = {}
        self.robot_arms: Dict[str, RobotArm] = {}
        self.execution_history: List[ExecutionResult] = []

        # LLM client (set in ITEM-2; None means use heuristic fallback)
        self.llm_client = None
        self._init_llm_client()

        # Initialize Harness components
        self._init_harness()

        # Initialize planner and code generator
        self._init_planner_and_generator()

        # Initialize robot arms from config
        self._init_robot_arms()

        logger.info(
            "SchedulingAgent initialized: %d arms, LLM=%s",
            len(self.robot_arms),
            "enabled" if self.llm_client else "disabled (heuristic fallback)",
        )

    # ------------------------------------------------------------------
    # Initialization helpers
    # ------------------------------------------------------------------

    def _init_llm_client(self):
        """Initialize the LLM client based on configuration.

        Uses the SyncLLMClient which provides synchronous generate()
        and generate_structured() methods for the planner and code
        generator.  Falls back to heuristic mode if LLM is unavailable.
        """
        import os

        # Load .env file if present
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        llm_config = self.config.get("llm", {})
        if not llm_config:
            logger.info("No LLM config; using heuristic fallback")
            return

        # Resolve API key (from config or env var)
        api_key = llm_config.get("api_key") or os.environ.get(
            llm_config.get("api_key_env", "OPENAI_API_KEY"), ""
        )
        api_base = llm_config.get("api_base", "")
        model = llm_config.get("model", "")

        if not api_key or not api_base or not model:
            logger.warning(
                "LLM config incomplete (api_key=%s, api_base=%s, model=%s); "
                "using heuristic fallback",
                bool(api_key),
                bool(api_base),
                bool(model),
            )
            return

        try:
            from agent.llm_clients.sync_client import SyncLLMClient

            self.llm_client = SyncLLMClient(
                {
                    "api_key": api_key,
                    "api_base": api_base,
                    "model": model,
                    "temperature": llm_config.get("temperature", 0.7),
                    "max_tokens": llm_config.get("max_tokens", 4096),
                    "max_retries": llm_config.get("max_retries", 3),
                    "retry_delay": llm_config.get("retry_delay", 1.0),
                }
            )
            logger.info("LLM client initialized: model=%s", model)
        except Exception as e:
            logger.warning(
                "Failed to initialize LLM client (%s); using heuristic fallback", e
            )
            self.llm_client = None

    def _init_harness(self):
        """Initialize all Harness Engineering components."""
        harness_config = self.config.get("harness", {})

        # Import here to avoid circular dependencies
        from harness.exception_handler import ExceptionHandler
        from harness.feedback_loop import FeedbackLoop
        from harness.resource_allocator import ResourceAllocator
        from harness.result_validator import ResultValidator
        from harness.task_decomposer import TaskDecomposer

        self.task_decomposer = TaskDecomposer(harness_config)
        self.resource_allocator = ResourceAllocator(harness_config)
        self.result_validator = ResultValidator(harness_config.get("validation", {}))
        self.exception_handler = ExceptionHandler(
            harness_config.get("exception_handling", {})
        )
        self.feedback_loop = FeedbackLoop(harness_config.get("feedback", {}))

        logger.info("Harness components initialized")

    def _init_planner_and_generator(self):
        """Initialize the task planner and code generator."""
        from agent.code_generator import CodeGenerator
        from agent.planner import TaskPlanner

        self.planner = TaskPlanner(self.config, llm_client=self.llm_client)
        self.code_generator = CodeGenerator(self.config, llm_client=self.llm_client)

        logger.info("Planner and code generator initialized")

    def _init_robot_arms(self):
        """Initialize robot arms from configuration."""
        arms_config = self.config.get("robot_arms", [])
        for arm_config in arms_config:
            pos = arm_config.get("base_position") or arm_config.get("position") or {}
            arm = RobotArm(
                id=arm_config["id"],
                name=arm_config.get("name", arm_config["id"]),
                capabilities=arm_config.get("capabilities", []),
                position=pos,
                max_load=arm_config.get("max_payload", arm_config.get("max_load", 5.0)),
            )
            self.robot_arms[arm.id] = arm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_scheduling(
        self,
        instruction: str,
        scene_config: Optional[Dict[str, Any]] = None,
        simulation=None,
    ) -> ExecutionResult:
        """
        Execute the complete scheduling pipeline.

        This is the main entry point called by run_simulation.py and
        evaluate.py.

        Args:
            instruction: Natural language instruction for the scheduling task.
            scene_config: Optional scene configuration with stations,
                         workpieces, robot_arms, constraints.
            simulation: Optional simulation interface. If None, a mock
                       simulator is created internally.

        Returns:
            ExecutionResult with all metrics, tasks, allocation, logs,
            feedback adjustments, and generated code.
        """
        execution_id = uuid.uuid4().hex[:8]
        logger.info("=== Scheduling execution %s started ===", execution_id)
        logger.info("Instruction: %s", instruction[:100])

        scene_config = scene_config or {}

        # Merge robot arms from scene into agent config if needed
        if "robot_arms" in scene_config and not self.robot_arms:
            self.config["robot_arms"] = scene_config["robot_arms"]
            self._init_robot_arms()

        # --- Step 1: Task decomposition ---
        logger.info("[Step 1] Task decomposition")
        plan = self.planner.create_plan(instruction, scene_config)
        tasks = self._convert_plan_tasks(plan.tasks)
        logger.info("Decomposed into %d tasks", len(tasks))

        if not tasks:
            logger.warning("No tasks generated; returning empty result")
            return ExecutionResult(
                execution_id=execution_id,
                instruction=instruction,
                tasks=[],
                allocation={},
                makespan=0.0,
                task_success_rate=0.0,
                resource_utilization=0.0,
                constraint_violations=0,
            )

        # --- Step 2: Resource allocation ---
        logger.info("[Step 2] Resource allocation")
        allocation = self.resource_allocator.allocate(
            tasks, list(self.robot_arms.values())
        )
        # Update tasks with assigned arms
        for task in tasks:
            task.assigned_arm = allocation.get(task.id)
        logger.info("Allocation: %s", allocation)

        # --- Step 3: Code generation ---
        logger.info("[Step 3] Code generation")
        generated_codes: Dict[str, str] = {}
        for task in tasks:
            arm_id = allocation.get(task.id)
            if not arm_id or arm_id not in self.robot_arms:
                continue
            arm = self.robot_arms[arm_id]

            # Extract parameters from scene for code generation
            params = self._build_code_parameters(task, scene_config)

            gen_code = self.code_generator.generate(
                task_name=task.name,
                task_description=task.description,
                operation_type=task.operation_type,
                arm_id=arm_id,
                required_capabilities=task.required_capabilities,
                parameters=params,
            )
            generated_codes[task.id] = gen_code.code

        logger.info("Generated code for %d tasks", len(generated_codes))

        # --- Step 4: Simulation execution ---
        logger.info("[Step 4] Simulation execution")
        if simulation is None:
            simulation = self._create_default_simulation(scene_config)

        execution_log, sim_total_time = self._execute_tasks(
            tasks, allocation, simulation, plan, generated_codes,
            scene_config=scene_config,
        )

        # --- Step 4b: Result validation ---
        logger.info("[Step 4b] Result validation")
        validation_result = self.result_validator.validate(
            {
                "tasks": [
                    {
                        "id": t.id,
                        "status": t.status.value,
                        "duration": (t.end_time or 0) - (t.start_time or 0),
                    }
                    for t in tasks
                ],
                "total_duration": sim_total_time,
                "resource_usage": (
                    {
                        arm_id: sum(
                            (e["end_time"] - e["start_time"])
                            for e in execution_log
                            if e["arm_id"] == arm_id
                        )
                        for arm_id in set(e["arm_id"] for e in execution_log)
                    }
                    if execution_log
                    else {}
                ),
            }
        )
        if not validation_result.is_valid:
            logger.warning("Validation failed: %s", validation_result.summary)
        else:
            logger.info("Validation passed: %s", validation_result.summary)

        # --- Step 5: Feedback collection & analysis ---
        logger.info("[Step 5] Feedback analysis")
        analysis = self.feedback_loop.analyze_feedback()
        adjustments = self.feedback_loop.adjust_strategy(analysis)
        feedback_adjustments = [
            {
                "task_id": "global",
                "adjustment": {
                    "target_module": adj.target_module,
                    "parameter": adj.parameter,
                    "old_value": adj.old_value,
                    "new_value": adj.new_value,
                    "reason": adj.reason,
                },
            }
            for adj in adjustments
        ]

        # Apply feedback adjustments to target modules (close the loop)
        for adj in adjustments:
            if adj.target_module == "resource_allocator":
                self.resource_allocator.update_config({adj.parameter: adj.new_value})
            elif adj.target_module == "exception_handler":
                self.exception_handler.update_config({adj.parameter: adj.new_value})
            elif adj.target_module == "code_generator":
                self.code_generator.update_config({adj.parameter: adj.new_value})

        logger.info(
            "Feedback: score=%.2f, %d adjustments, bottlenecks=%s",
            analysis.performance_score,
            len(adjustments),
            analysis.bottlenecks,
        )

        # --- Step 6: Metrics calculation ---
        logger.info("[Step 6] Metrics calculation")
        makespan = self._calculate_makespan(execution_log)
        task_success_rate = self._calculate_success_rate(tasks)
        resource_utilization = self._calculate_utilization(
            execution_log, len(self.robot_arms), makespan
        )
        constraint_violations = self._count_violations(execution_log)
        # Add violations detected by the result validator
        if not validation_result.is_valid:
            constraint_violations += int(
                validation_result.metrics.get("critical_violations", 0)
            )

        # --- Build result ---
        result = ExecutionResult(
            execution_id=execution_id,
            instruction=instruction,
            tasks=tasks,
            allocation=allocation,
            makespan=makespan,
            task_success_rate=task_success_rate,
            resource_utilization=resource_utilization,
            constraint_violations=constraint_violations,
            execution_log=execution_log,
            feedback_adjustments=feedback_adjustments,
            generated_codes=generated_codes,
        )

        self.execution_history.append(result)
        logger.info(
            "=== Execution %s complete: makespan=%.3f, success=%.1f%%, "
            "util=%.1f%%, violations=%d ===",
            execution_id,
            makespan,
            task_success_rate * 100,
            resource_utilization * 100,
            constraint_violations,
        )

        return result

    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate aggregate performance metrics from execution history."""
        if not self.execution_history:
            return {}

        n = len(self.execution_history)
        return {
            "average_makespan": sum(r.makespan for r in self.execution_history) / n,
            "average_success_rate": sum(
                r.task_success_rate for r in self.execution_history
            )
            / n,
            "average_resource_utilization": sum(
                r.resource_utilization for r in self.execution_history
            )
            / n,
            "total_constraint_violations": sum(
                r.constraint_violations for r in self.execution_history
            ),
            "total_executions": n,
        }

    # ------------------------------------------------------------------
    # Internal helpers — task conversion
    # ------------------------------------------------------------------

    def _convert_plan_tasks(self, plan_tasks: list) -> List[Task]:
        """Convert TaskNode objects from the planner into Task objects."""
        tasks = []
        for pt in plan_tasks:
            task = Task(
                id=pt.id,
                name=pt.name,
                description=pt.description,
                dependencies=list(pt.dependencies),
                operation_type=pt.operation_type,
                station_id=pt.station_id,
                workpiece_id=pt.workpiece_id,
                required_capabilities=list(pt.required_capabilities),
                estimated_duration=pt.estimated_duration,
                priority=pt.priority,
            )
            tasks.append(task)
        return tasks

    # ------------------------------------------------------------------
    # Internal helpers — code generation parameters
    # ------------------------------------------------------------------

    def _build_code_parameters(
        self, task: Task, scene_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build parameters dict for the code generator from scene config."""
        params: Dict[str, Any] = {
            "estimated_duration": task.estimated_duration,
        }

        # Find station position
        stations = scene_config.get("stations", [])
        if task.station_id:
            station = next(
                (s for s in stations if s.get("id") == task.station_id), None
            )
            if station:
                params["target_position"] = station.get("position", {})
                params["station_name"] = station.get("name", task.station_id)

        # Find workpiece initial position
        workpieces = scene_config.get("workpieces", [])
        if task.workpiece_id:
            wp = next((w for w in workpieces if w.get("id") == task.workpiece_id), None)
            if wp:
                params["source_position"] = wp.get("initial_position", {})
                params["workpiece_type"] = wp.get("type", "generic")
                params["workpiece_id"] = task.workpiece_id

        return params

    # ------------------------------------------------------------------
    # Internal helpers — simulation execution
    # ------------------------------------------------------------------

    def _create_default_simulation(self, scene_config: Dict[str, Any]):
        """Create simulation backend. Isaac Sim by default; mock only if explicitly requested."""
        sim_config = self.config.get("simulation", {})
        backend = sim_config.get("backend", "isaac")

        if backend == "mock":
            logger.info("Mock backend explicitly requested via config")
            return self._create_mock_simulation(scene_config, sim_config)

        # Default: try Isaac Sim
        try:
            from simulation.isaac_sim import IsaacSimInterface

            sim = IsaacSimInterface(fallback_to_mock=False)
            sim.initialize()
            sim.load_scene(scene_config)
            logger.info("Created Isaac Sim simulation (real physics)")
            return sim
        except ImportError:
            if backend == "isaac":
                # Isaac Sim explicitly requested but not available
                raise RuntimeError(
                    "Isaac Sim requested but not installed. "
                    "Install with: pip install isaacsim --extra-index-url https://pypi.nvidia.com"
                )
            # Auto mode: fall back to mock with warning
            logger.warning("Isaac Sim not available, falling back to mock simulator")
            return self._create_mock_simulation(scene_config, sim_config)

    def _create_mock_simulation(self, scene_config: Dict[str, Any], sim_config: Dict[str, Any]):
        """Create a mock simulator (only when explicitly requested or as fallback)."""
        from simulation.mock_simulator import MockSimulator

        mock_config = sim_config.get("mock", {})

        sim = MockSimulator(
            failure_probabilities={
                "default": mock_config.get("failure_probability", 0.0)
            },
            time_scale=1.0,
            seed=42,
        )
        sim.initialize()

        mock_scene = self._build_mock_scene(scene_config)
        sim.load_scene(mock_scene)

        logger.info("Created mock simulator")
        return sim

    def _build_mock_scene(self, scene_config: Dict[str, Any]) -> dict:
        """Build a scene config dict for the mock simulator."""
        robot_arms = []
        for arm in scene_config.get("robot_arms", []):
            pos = arm.get("base_position") or arm.get("position", {})
            robot_arms.append(
                {
                    "id": arm["id"],
                    "position": pos,
                }
            )

        objects = []
        for wp in scene_config.get("workpieces", []):
            pos = wp.get("initial_position", {})
            objects.append(
                {
                    "id": wp["id"],
                    "type": wp.get("type", "generic"),
                    "position": pos,
                }
            )

        return {"robot_arms": robot_arms, "objects": objects}

    def _execute_tasks(
        self,
        tasks: List[Task],
        allocation: Dict[str, str],
        simulation,
        plan,
        generated_codes: Optional[Dict[str, str]] = None,
        scene_config: Optional[Dict[str, Any]] = None,
    ) -> tuple:
        """
        Execute tasks in topological order within the simulation.

        If generated_codes is provided, the generated Python code is
        actually executed via an ArmInterface adapter that drives the
        simulation. Otherwise, a simple action-based fallback is used.

        Returns:
            Tuple of (execution_log, total_sim_time).
        """
        from simulation.arm_interface import execute_generated_code

        execution_log: List[Dict[str, Any]] = []
        sim_time = 0.0

        # Get execution order from plan (topological levels)
        try:
            execution_levels = plan.get_execution_order()
        except Exception:
            execution_levels = [[t.id for t in tasks]]

        task_map = {t.id: t for t in tasks}
        task_end_times: Dict[str, float] = {}

        for level in execution_levels:
            level_end_time = sim_time
            level_arm_end_times = {}

            for task_id in level:
                task = task_map.get(task_id)
                if task is None:
                    continue

                arm_id = allocation.get(task_id)
                if not arm_id:
                    logger.warning("No arm assigned for task %s; skipping", task_id)
                    task.status = TaskStatus.CANCELLED
                    continue

                # Determine start time (after all dependencies complete
                # and after any prior task on the same arm in this level)
                start_time = sim_time
                for dep_id in task.dependencies:
                    if dep_id in task_end_times:
                        start_time = max(start_time, task_end_times[dep_id])
                if arm_id in level_arm_end_times:
                    start_time = max(start_time, level_arm_end_times[arm_id])

                # --- Execute the generated code in simulation ---
                attempt = 1
                strategy = self.feedback_loop.get_current_strategy()
                max_attempts = int(strategy.get("retry_count", 3))
                exec_result = None
                recovery = None
                last_exception = None

                while attempt <= max_attempts:
                    code = (generated_codes or {}).get(task_id)
                    if code:
                        # Execute generated code via ArmInterface
                        exec_result = execute_generated_code(
                            code_str=code,
                            arm_id=arm_id,
                            simulation=simulation,
                            estimated_duration=task.estimated_duration,
                        )
                    else:
                        # Fallback: simple action execution
                        action = self._build_simulation_action(task, simulation)
                        try:
                            sim_result = simulation.execute_action(arm_id, action)
                            exec_result = {
                                "success": sim_result.success,
                                "duration": sim_result.duration,
                                "error": sim_result.error_message,
                            }
                        except Exception as exc:
                            exec_result = {
                                "success": False,
                                "duration": 0.0,
                                "error": str(exc),
                            }

                    if exec_result.get("success", False):
                        if recovery and last_exception:
                            self.exception_handler.record_exception(
                                last_exception, recovery, "success"
                            )
                        break

                    # Classify and handle the failure via exception_handler
                    error_msg = exec_result.get("error", "Unknown error")
                    last_exception = RuntimeError(error_msg)
                    recovery = self.exception_handler.handle(
                        last_exception,
                        {
                            "task_id": task_id,
                            "arm_id": arm_id,
                            "attempt": attempt,
                            "module_name": "execution",
                        },
                    )

                    if recovery.action_type == RecoveryActionType.SKIP:
                        logger.warning(
                            "Exception handler SKIP for task %s after %d attempts",
                            task_id,
                            attempt,
                        )
                        break
                    elif recovery.action_type == RecoveryActionType.REPLAN:
                        logger.warning(
                            "Exception handler REPLAN suggested for task %s",
                            task_id,
                        )

                    logger.warning(
                        "Task %s attempt %d failed: %s (recovery=%s)",
                        task_id,
                        attempt,
                        error_msg,
                        recovery.action_type.value,
                    )

                    # --- Code regeneration with feedback (close the loop) ---
                    if attempt < max_attempts:
                        feedback_data = {
                            "original_code": code or "",
                            "execution_result": exec_result or {},
                            "error": error_msg,
                        }
                        try:
                            if not self.llm_client:
                                cur_speed = self.code_generator.speed_factor
                                cur_force = self.code_generator.force_factor
                                self.code_generator.update_config(
                                    {
                                        "code_gen_speed_factor": max(
                                            0.1, cur_speed * 0.85
                                        ),
                                        "code_gen_force_factor": min(
                                            3.0, cur_force * 1.1
                                        ),
                                    }
                                )
                            params = self._build_code_parameters(
                                task, scene_config or {}
                            )
                            regen = self.code_generator.generate(
                                task_name=task.name,
                                task_description=task.description,
                                operation_type=task.operation_type,
                                arm_id=arm_id,
                                required_capabilities=task.required_capabilities,
                                parameters=params,
                                feedback=feedback_data,
                            )
                            if regen and regen.code:
                                generated_codes[task_id] = regen.code
                                code = regen.code
                                logger.info(
                                    "Regenerated code for task %s (method=%s)",
                                    task_id,
                                    regen.metadata.get("method", "unknown"),
                                )
                        except Exception as regen_err:
                            logger.debug(
                                "Code regeneration failed for task %s: %s",
                                task_id,
                                regen_err,
                            )

                    attempt += 1

                # Record results
                duration = exec_result.get("duration", 0) if exec_result else 0
                # Use estimated_duration as minimum if duration is too small
                if duration < 0.001:
                    duration = task.estimated_duration
                success = exec_result.get("success", False) if exec_result else False
                end_time = start_time + duration

                task.start_time = start_time
                task.end_time = end_time
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.result = exec_result or {}

                task_end_times[task_id] = end_time
                level_arm_end_times[arm_id] = end_time

                log_entry = {
                    "task_id": task_id,
                    "arm_id": arm_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": task.status.value,
                    "attempt": attempt,
                }
                if not success and exec_result and exec_result.get("error"):
                    log_entry["error"] = exec_result["error"]
                if exec_result and exec_result.get("action_count"):
                    log_entry["primitives_called"] = exec_result["action_count"]
                execution_log.append(log_entry)

                # Collect feedback for this task
                self.feedback_loop.collect_feedback(
                    {
                        "task_id": task_id,
                        "arm_id": arm_id,
                        "status": "success" if success else "failure",
                        "duration": duration,
                        "resource_usage": {arm_id: duration},
                        "errors": (
                            [exec_result["error"]]
                            if exec_result and exec_result.get("error")
                            else []
                        ),
                    }
                )

                level_end_time = max(level_end_time, end_time)

            sim_time = level_end_time

        return execution_log, sim_time

    def _build_simulation_action(self, task: Task, simulation) -> dict:
        """Build a simulation action dict from a task."""
        action_type = _map_action_type(task.operation_type)

        action: Dict[str, Any] = {
            "type": action_type,
            "estimated_duration": task.estimated_duration,
        }

        # Add target workpiece if available
        if task.workpiece_id:
            action["target"] = task.workpiece_id

        # Add position from station if available
        if task.parameters.get("target_position"):
            action["position"] = task.parameters["target_position"]
        elif task.station_id:
            # Try to get position from simulation state
            try:
                state = simulation.get_state()
                for obj_id, obj_state in state.object_states.items():
                    if obj_id == task.station_id:
                        action["position"] = {
                            "x": obj_state.position.x,
                            "y": obj_state.position.y,
                            "z": obj_state.position.z,
                        }
                        break
            except Exception:
                pass

        return action

    # ------------------------------------------------------------------
    # Internal helpers — metrics
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_makespan(execution_log: List[Dict[str, Any]]) -> float:
        """Calculate makespan from execution log."""
        if not execution_log:
            return 0.0
        earliest = min(e["start_time"] for e in execution_log)
        latest = max(e["end_time"] for e in execution_log)
        return latest - earliest

    @staticmethod
    def _calculate_success_rate(tasks: List[Task]) -> float:
        """Calculate task success rate."""
        if not tasks:
            return 0.0
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(tasks)

    @staticmethod
    def _calculate_utilization(
        execution_log: List[Dict[str, Any]],
        num_arms: int,
        makespan: float,
    ) -> float:
        """Calculate resource utilization."""
        if makespan <= 0 or num_arms <= 0:
            return 0.0
        total_busy = sum(
            e["end_time"] - e["start_time"]
            for e in execution_log
            if e["end_time"] > e["start_time"]
        )
        util = total_busy / (makespan * num_arms)
        return min(util, 1.0)

    @staticmethod
    def _count_violations(execution_log: List[Dict[str, Any]]) -> int:
        """Count constraint violations (overlapping tasks on same arm)."""
        violations = 0

        # Group by arm
        arm_intervals: Dict[str, list] = {}
        for e in execution_log:
            arm_intervals.setdefault(e["arm_id"], []).append(
                (e["start_time"], e["end_time"], e["task_id"])
            )

        # Check for overlaps
        for arm_id, intervals in arm_intervals.items():
            intervals.sort(key=lambda x: x[0])
            for i in range(len(intervals) - 1):
                if intervals[i][1] > intervals[i + 1][0]:
                    violations += 1

        return violations
