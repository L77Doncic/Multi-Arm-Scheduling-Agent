"""
Multi-Arm Scheduling Agent Core Module

This module implements the core LLM-driven agent for multi-arm scheduling.
It orchestrates task decomposition, resource allocation, code generation,
simulation execution, and closed-loop feedback.
"""

import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task data class."""
    id: str
    name: str
    description: str
    dependencies: List[str]
    operation_type: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    assigned_arm: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    generated_code: Optional[str] = None
    station_id: Optional[str] = None
    workpiece_id: Optional[str] = None


@dataclass
class RobotArm:
    """Robot arm data class."""
    id: str
    name: str
    capabilities: List[str]
    current_task: Optional[str] = None
    is_busy: bool = False
    position: Optional[Dict[str, float]] = None
    task_history: List[str] = field(default_factory=list)
    total_busy_time: float = 0.0


@dataclass
class ExecutionResult:
    """Result of a complete scheduling execution."""
    execution_id: str
    instruction: str
    tasks: List[Task]
    allocation: Dict[str, str]
    makespan: float
    task_success_rate: float
    resource_utilization: float
    constraint_violations: int
    generated_codes: Dict[str, str]
    execution_log: List[Dict[str, Any]]
    feedback_adjustments: List[Dict[str, Any]]
    simulation_results: Optional[Dict[str, Any]] = None


class SchedulingAgent:
    """
    LLM-driven multi-arm scheduling agent.

    This agent uses large language models to intelligently decompose tasks,
    allocate resources, and generate executable code for robotic arms.
    It operates within a Harness Engineering constraint framework with
    closed-loop feedback for dynamic strategy adjustment.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scheduling agent.

        Args:
            config: Configuration dictionary containing LLM settings,
                   robot arm definitions, and task parameters.
        """
        self.config = config
        self.tasks: Dict[str, Task] = {}
        self.robot_arms: Dict[str, RobotArm] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.strategy_params: Dict[str, Any] = {
            'default_timeout': config.get('task', {}).get('default_timeout', 30.0),
            'max_retries': config.get('harness', {}).get('validation', {}).get('max_retries', 3),
            'parallel_execution': config.get('task', {}).get('parallel_execution', True),
            'max_concurrent': config.get('task', {}).get('max_concurrent_tasks', 3),
        }

        # Initialize subsystems
        self._init_llm_client()
        self._init_robot_arms()
        self._init_harness()

        logger.info("SchedulingAgent initialized with %d robot arms",
                     len(self.robot_arms))

    def _init_llm_client(self):
        """Initialize the LLM client based on configuration."""
        llm_config = self.config.get('llm', {})
        provider = llm_config.get('provider', '')

        if provider and provider != 'local':
            try:
                from .llm_clients.factory import create_llm_client
                self.llm_client = create_llm_client(llm_config)
                logger.info("LLM client initialized: %s/%s",
                            provider, llm_config.get('model', 'unknown'))
            except Exception as e:
                logger.warning("Failed to init LLM client (%s), using heuristic mode", e)
                self.llm_client = None
        else:
            self.llm_client = None
            logger.info("No LLM provider configured, using heuristic mode")

    def _init_robot_arms(self):
        """Initialize robot arms from configuration."""
        arms_config = self.config.get('robot_arms', [])
        for arm_config in arms_config:
            arm = RobotArm(
                id=arm_config['id'],
                name=arm_config['name'],
                capabilities=arm_config.get('capabilities', []),
                position=arm_config.get('base_position') or arm_config.get('workspace')
            )
            self.robot_arms[arm.id] = arm

    def _init_harness(self):
        """Initialize Harness Engineering modules."""
        harness_config = self.config.get('harness', {})

        from .planner import TaskPlanner
        from .code_generator import CodeGenerator

        self.planner = TaskPlanner(self.config, self.llm_client)
        self.code_generator = CodeGenerator(self.config, self.llm_client)

        # Lazy-init harness modules (they may not exist yet during partial setup)
        self._task_decomposer = None
        self._resource_allocator = None
        self._result_validator = None
        self._exception_handler = None
        self._feedback_loop = None

    @property
    def task_decomposer(self):
        if self._task_decomposer is None:
            try:
                from ..harness.task_decomposer import TaskDecomposer
                self._task_decomposer = TaskDecomposer(self.config)
            except ImportError:
                pass
        return self._task_decomposer

    @property
    def resource_allocator(self):
        if self._resource_allocator is None:
            try:
                from ..harness.resource_allocator import ResourceAllocator
                self._resource_allocator = ResourceAllocator(self.config)
            except ImportError:
                pass
        return self._resource_allocator

    @property
    def result_validator(self):
        if self._result_validator is None:
            try:
                from ..harness.result_validator import ResultValidator
                self._result_validator = ResultValidator(self.config)
            except ImportError:
                pass
        return self._result_validator

    @property
    def exception_handler(self):
        if self._exception_handler is None:
            try:
                from ..harness.exception_handler import ExceptionHandler
                self._exception_handler = ExceptionHandler(self.config)
            except ImportError:
                pass
        return self._exception_handler

    @property
    def feedback_loop(self):
        if self._feedback_loop is None:
            try:
                from ..harness.feedback_loop import FeedbackLoop
                self._feedback_loop = FeedbackLoop(self.config)
            except ImportError:
                pass
        return self._feedback_loop

    def decompose_task(self, natural_language_instruction: str,
                       scene_config: Optional[Dict] = None) -> List[Task]:
        """
        Decompose a natural language instruction into subtasks.

        Args:
            natural_language_instruction: The instruction to decompose.
            scene_config: Optional scene configuration.

        Returns:
            List of Task objects representing the decomposed subtasks.
        """
        logger.info("Decomposing task: %s", natural_language_instruction[:80])

        # Use the planner to create a task plan
        plan = self.planner.create_plan(natural_language_instruction, scene_config)

        # Convert plan nodes to Task objects
        tasks = []
        for node in plan.tasks:
            task = Task(
                id=node.id,
                name=node.name,
                description=node.description,
                dependencies=list(node.dependencies),
                operation_type=node.operation_type,
                required_capabilities=list(node.required_capabilities),
                estimated_duration=node.estimated_duration,
                station_id=node.station_id,
                workpiece_id=node.workpiece_id,
            )
            tasks.append(task)
            self.tasks[task.id] = task

        logger.info("Decomposed into %d tasks", len(tasks))
        return tasks

    def allocate_resources(self, tasks: List[Task]) -> Dict[str, str]:
        """
        Allocate robot arms to tasks based on capabilities and availability.

        Args:
            tasks: List of tasks to allocate.

        Returns:
            Dictionary mapping task IDs to robot arm IDs.
        """
        logger.info("Allocating resources for %d tasks", len(tasks))

        # Use resource allocator if available
        if self.resource_allocator:
            task_dicts = []
            for t in tasks:
                task_dicts.append({
                    'id': t.id,
                    'name': t.name,
                    'required_capabilities': t.required_capabilities,
                    'estimated_duration': t.estimated_duration,
                    'dependencies': t.dependencies,
                    'priority': 1,
                })

            arm_dicts = []
            for arm in self.robot_arms.values():
                arm_dicts.append({
                    'id': arm.id,
                    'name': arm.name,
                    'capabilities': arm.capabilities,
                })

            allocation = self.resource_allocator.allocate(task_dicts, arm_dicts)
        else:
            # Fallback: simple greedy allocation
            allocation = self._greedy_allocate(tasks)

        # Update task assignments
        for task_id, arm_id in allocation.items():
            if task_id in self.tasks:
                self.tasks[task_id].assigned_arm = arm_id
            if arm_id in self.robot_arms:
                self.robot_arms[arm_id].task_history.append(task_id)

        logger.info("Resource allocation complete: %d assignments", len(allocation))
        return allocation

    def _greedy_allocate(self, tasks: List[Task]) -> Dict[str, str]:
        """Simple greedy allocation: match capabilities, balance load."""
        allocation: Dict[str, str] = {}
        arm_load: Dict[str, float] = {a.id: 0.0 for a in self.robot_arms.values()}

        # Sort tasks by priority (lower priority number = higher priority)
        sorted_tasks = sorted(tasks, key=lambda t: (
            -len(t.dependencies),  # Independent tasks first
            t.estimated_duration,   # Shorter tasks first
        ))

        for task in sorted_tasks:
            best_arm: Optional[str] = None
            best_score = -1.0

            for arm in self.robot_arms.values():
                # Check capability match
                caps_match = len(
                    set(task.required_capabilities) & set(arm.capabilities)
                )
                caps_needed = max(len(task.required_capabilities), 1)
                cap_score = caps_match / caps_needed

                if cap_score < 0.5:
                    continue  # Insufficient capabilities

                # Balance score (prefer less loaded arms)
                load_score = 1.0 / (1.0 + arm_load[arm.id])
                total_score = cap_score * 0.7 + load_score * 0.3

                if total_score > best_score:
                    best_score = total_score
                    best_arm = arm.id

            if best_arm:
                allocation[task.id] = best_arm
                arm_load[best_arm] += task.estimated_duration

        return allocation

    def generate_code(self, task: Task, arm: RobotArm,
                      feedback: Optional[Dict] = None) -> str:
        """
        Generate executable code for a specific task and robot arm.

        Args:
            task: The task to generate code for.
            arm: The robot arm that will execute the task.
            feedback: Optional feedback from previous execution.

        Returns:
            Generated Python code as a string.
        """
        logger.info("Generating code for task %s on arm %s", task.id, arm.id)

        result = self.code_generator.generate(
            task_name=task.name,
            task_description=task.description,
            operation_type=task.operation_type,
            arm_id=arm.id,
            required_capabilities=task.required_capabilities,
            parameters={
                'estimated_duration': task.estimated_duration,
                'station_id': task.station_id,
            },
            feedback=feedback
        )

        task.generated_code = result.code
        return result.code

    def execute_scheduling(self, instruction: str,
                           scene_config: Optional[Dict] = None,
                           simulation=None) -> ExecutionResult:
        """
        Execute the complete scheduling pipeline with closed-loop feedback.

        Args:
            instruction: Natural language instruction for the scheduling task.
            scene_config: Optional scene configuration.
            simulation: Optional simulation interface for execution.

        Returns:
            ExecutionResult with comprehensive execution data.
        """
        execution_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        logger.info("Starting scheduling execution %s", execution_id)

        # === Phase 1: Task Decomposition ===
        tasks = self.decompose_task(instruction, scene_config)

        # === Phase 2: Resource Allocation ===
        allocation = self.allocate_resources(tasks)

        # === Phase 3: Code Generation ===
        for task in tasks:
            arm_id = allocation.get(task.id)
            if arm_id and arm_id in self.robot_arms:
                arm = self.robot_arms[arm_id]
                self.generate_code(task, arm)

        # === Phase 4: Execution with Feedback Loop ===
        execution_log: List[Dict[str, Any]] = []
        feedback_adjustments: List[Dict[str, Any]] = []
        max_retries = self.strategy_params.get('max_retries', 3)

        # Get execution order (topological)
        execution_levels = self._get_execution_levels(tasks)

        for level in execution_levels:
            for task_id in level:
                task = self.tasks.get(task_id)
                if not task:
                    continue

                arm_id = allocation.get(task_id)
                if not arm_id or arm_id not in self.robot_arms:
                    continue

                arm = self.robot_arms[arm_id]

                # Execute with retry logic
                result = self._execute_task_with_retry(
                    task, arm, simulation, max_retries, execution_log
                )

                # Collect feedback
                if self.feedback_loop:
                    feedback = self.feedback_loop.collect_feedback({
                        'task_id': task.id,
                        'arm_id': arm_id,
                        'status': task.status.value,
                        'duration': (task.end_time or 0) - (task.start_time or 0),
                        'result': task.result,
                    })
                    analysis = self.feedback_loop.analyze_feedback(feedback)
                    if analysis.recommendations:
                        adjustment = self.feedback_loop.adjust_strategy(analysis)
                        if adjustment:
                            feedback_adjustments.append({
                                'task_id': task.id,
                                'adjustment': adjustment,
                            })

        total_time = time.time() - start_time

        # === Phase 5: Compute Metrics ===
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        makespan = total_time
        success_rate = completed / len(tasks) if tasks else 1.0

        # Resource utilization
        total_busy = sum(a.total_busy_time for a in self.robot_arms.values())
        total_arm_time = len(self.robot_arms) * makespan if makespan > 0 else 1.0
        resource_util = total_busy / total_arm_time

        # Constraint violations
        violations = sum(
            1 for log in execution_log
            if log.get('status') == 'failed' or log.get('constraint_violation', False)
        )

        # Generated codes
        codes = {t.id: t.generated_code or "" for t in tasks if t.generated_code}

        result = ExecutionResult(
            execution_id=execution_id,
            instruction=instruction,
            tasks=tasks,
            allocation=allocation,
            makespan=makespan,
            task_success_rate=success_rate,
            resource_utilization=resource_util,
            constraint_violations=violations,
            generated_codes=codes,
            execution_log=execution_log,
            feedback_adjustments=feedback_adjustments,
        )

        self.execution_history.append({
            'execution_id': execution_id,
            'instruction': instruction,
            'makespan': makespan,
            'success_rate': success_rate,
            'resource_utilization': resource_util,
            'violations': violations,
            'num_tasks': len(tasks),
        })

        logger.info("Execution %s complete: makespan=%.2f, success=%.1f%%, util=%.1f%%",
                     execution_id, makespan, success_rate * 100, resource_util * 100)
        return result

    def _execute_task_with_retry(self, task: Task, arm: RobotArm,
                                  simulation, max_retries: int,
                                  execution_log: List[Dict]) -> Dict:
        """Execute a single task with retry logic."""
        for attempt in range(max_retries + 1):
            task.status = TaskStatus.IN_PROGRESS
            task.start_time = time.time()
            arm.is_busy = True
            arm.current_task = task.id

            try:
                if simulation:
                    # Execute in simulation
                    # Map operation types to simulator-recognized action types
                    action_type = self._map_action_type(task.operation_type)
                    action = {
                        'type': action_type,
                        'task_id': task.id,
                        'code': task.generated_code,
                        'parameters': {
                            'station_id': task.station_id,
                            'workpiece_id': task.workpiece_id,
                        }
                    }
                    sim_result = simulation.execute_action(arm.id, action)
                    success = sim_result.success
                    task.result = {
                        'success': success,
                        'duration': sim_result.duration,
                        'position': sim_result.position,
                        'error': sim_result.error_message,
                    }
                else:
                    # Simulate execution locally
                    import random
                    time.sleep(min(task.estimated_duration * 0.01, 0.1))  # Accelerated
                    success = random.random() > 0.05  # 95% success rate
                    task.result = {
                        'success': success,
                        'duration': task.estimated_duration,
                        'error': None if success else 'Simulated failure',
                    }

                task.end_time = time.time()
                arm.total_busy_time += task.end_time - task.start_time

                if success:
                    task.status = TaskStatus.COMPLETED
                    execution_log.append({
                        'task_id': task.id,
                        'arm_id': arm.id,
                        'start_time': task.start_time,
                        'end_time': task.end_time,
                        'status': 'completed',
                        'attempt': attempt + 1,
                    })
                    break
                else:
                    task.status = TaskStatus.FAILED
                    error_msg = task.result.get('error', 'Unknown error')

                    # Handle exception
                    if self.exception_handler:
                        recovery = self.exception_handler.handle(
                            Exception(error_msg),
                            {'task_id': task.id, 'arm_id': arm.id, 'attempt': attempt}
                        )
                        if recovery.action_type == 'skip':
                            break

                    execution_log.append({
                        'task_id': task.id,
                        'arm_id': arm.id,
                        'start_time': task.start_time,
                        'end_time': task.end_time,
                        'status': 'failed',
                        'attempt': attempt + 1,
                        'error': error_msg,
                    })

                    if attempt < max_retries:
                        logger.info("Retrying task %s (attempt %d/%d)",
                                    task.id, attempt + 2, max_retries + 1)
                        # Refine code with feedback
                        if task.generated_code and arm:
                            self.generate_code(task, arm, feedback={
                                'original_code': task.generated_code,
                                'execution_result': task.result,
                                'error': error_msg,
                            })

            except Exception as e:
                task.end_time = time.time()
                task.status = TaskStatus.FAILED
                task.result = {'success': False, 'error': str(e)}
                logger.error("Task %s exception: %s", task.id, e)

                execution_log.append({
                    'task_id': task.id,
                    'arm_id': arm.id,
                    'start_time': task.start_time,
                    'end_time': task.end_time,
                    'status': 'error',
                    'attempt': attempt + 1,
                    'error': str(e),
                })

            finally:
                arm.is_busy = False
                arm.current_task = None

        return task.result or {}

    @staticmethod
    def _map_action_type(operation_type: str) -> str:
        """Map scenario operation types to simulator-recognized action types."""
        type_map = {
            'pick': 'pick',
            'pick_workpiece_from_feed': 'pick',
            'pick_from_feed': 'pick',
            'place': 'place',
            'package': 'place',
            'package_and_output': 'place',
            'output': 'place',
            'drop': 'place',
            'move': 'move',
            'transfer': 'move',
            'transport': 'move',
            'assemble': 'assemble',
            'assemble_components': 'assemble',
            'final_assembly': 'assemble',
            'join': 'assemble',
            'connect': 'assemble',
            'inspect': 'inspect',
            'quality_inspection': 'inspect',
            'quality_check': 'inspect',
            'verify': 'inspect',
            'tighten': 'tighten',
            'secure': 'tighten',
            'bolt': 'tighten',
            'weld': 'weld',
            'weld_joints': 'weld',
            'solder': 'weld',
            'prepare': 'move',
            'prepare_workpiece': 'move',
            'prep': 'move',
        }
        return type_map.get(operation_type, 'generic')

    def _get_execution_levels(self, tasks: List[Task]) -> List[List[str]]:
        """Get tasks grouped by execution level (topological order)."""
        task_map = {t.id: t for t in tasks}
        in_degree: Dict[str, int] = {t.id: 0 for t in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[task.id] += 1

        levels: List[List[str]] = []
        remaining = set(in_degree.keys())

        while remaining:
            level = [n for n in remaining if in_degree[n] == 0]
            if not level:
                # Break circular dependency
                level = [min(remaining)]
                logger.warning("Circular dependency, breaking at %s", level[0])

            levels.append(list(level))
            for node in level:
                remaining.discard(node)
                for task in tasks:
                    if node in task.dependencies and task.id in remaining:
                        in_degree[task.id] -= 1

        return levels

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics from execution history.

        Returns:
            Dictionary containing performance metrics.
        """
        if not self.execution_history:
            return {
                'average_makespan': 0.0,
                'average_success_rate': 0.0,
                'resource_utilization': 0.0,
                'constraint_violations': 0,
                'total_executions': 0,
            }

        n = len(self.execution_history)
        return {
            'average_makespan': sum(e['makespan'] for e in self.execution_history) / n,
            'average_success_rate': sum(e['success_rate'] for e in self.execution_history) / n,
            'resource_utilization': sum(e['resource_utilization'] for e in self.execution_history) / n,
            'constraint_violations': sum(e['violations'] for e in self.execution_history),
            'total_executions': n,
        }
