"""
Basic unit tests for Multi-Arm Scheduling Agent
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def test_import_agent():
    """Test that agent module can be imported."""
    from agent.core import RobotArm, SchedulingAgent, Task, TaskStatus

    assert SchedulingAgent is not None
    assert Task is not None
    assert RobotArm is not None
    assert TaskStatus is not None


def test_task_status_enum():
    """Test TaskStatus enum values."""
    from agent.core import TaskStatus

    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.IN_PROGRESS.value == "in_progress"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"


def test_task_creation():
    """Test Task data class creation."""
    from agent.core import Task, TaskStatus

    task = Task(
        id="task_001",
        name="Pick Component",
        description="Pick up component A from conveyor",
        dependencies=[],
        status=TaskStatus.PENDING,
    )
    assert task.id == "task_001"
    assert task.name == "Pick Component"
    assert task.status == TaskStatus.PENDING
    assert task.assigned_arm is None


def test_robot_arm_creation():
    """Test RobotArm data class creation."""
    from agent.core import RobotArm

    arm = RobotArm(
        id="arm_001", name="Left Arm", capabilities=["pick", "place", "move"]
    )
    assert arm.id == "arm_001"
    assert arm.name == "Left Arm"
    assert "pick" in arm.capabilities
    assert arm.is_busy is False


def test_scheduling_agent_initialization():
    """Test SchedulingAgent initialization."""
    from agent.core import SchedulingAgent

    config = {
        "robot_arms": [
            {"id": "arm_001", "name": "Test Arm", "capabilities": ["pick", "place"]}
        ]
    }
    agent = SchedulingAgent(config)
    assert len(agent.robot_arms) == 1
    assert "arm_001" in agent.robot_arms


def test_task_decomposer_import():
    """Test that task decomposer module can be imported."""
    from harness.task_decomposer import DecomposedTask, TaskDecomposer

    assert TaskDecomposer is not None
    assert DecomposedTask is not None


def test_task_decomposer_initialization():
    """Test TaskDecomposer initialization."""
    from harness.task_decomposer import TaskDecomposer

    config = {}
    decomposer = TaskDecomposer(config)
    assert decomposer.config == config
    assert decomposer.task_counter == 0


def test_task_decomposition():
    """Test basic task decomposition."""
    from harness.task_decomposer import TaskDecomposer

    config = {}
    decomposer = TaskDecomposer(config)

    instruction = "Pick up component A and place it on the assembly table"
    tasks = decomposer.decompose(instruction)

    assert isinstance(tasks, list)
    # Should decompose into at least one task
    assert len(tasks) >= 1


# ------------------------------------------------------------------
# Resource Allocator tests
# ------------------------------------------------------------------


def test_resource_allocator_basic_allocation():
    """Test basic task-to-arm allocation."""
    from harness.resource_allocator import ResourceAllocator

    config = {}
    allocator = ResourceAllocator(config)

    class FakeTask:
        def __init__(self, id, caps, dur=1.0, prio=1.0):
            self.id = id
            self.required_capabilities = caps
            self.estimated_duration = dur
            self.priority = prio
            self.dependencies = []

    class FakeArm:
        def __init__(self, id, caps, max_load=5.0):
            self.id = id
            self.capabilities = caps
            self.max_load = max_load
            self.current_load = 0.0
            self.position = (0.0, 0.0, 0.0)

    tasks = [FakeTask("t1", ["pick"]), FakeTask("t2", ["place"])]
    arms = [FakeArm("a1", ["pick", "place"]), FakeArm("a2", ["pick"])]

    result = allocator.allocate(tasks, arms)
    assert len(result) == 2
    assert "t1" in result
    assert "t2" in result


def test_resource_allocator_update_config():
    """Test runtime config updates from feedback loop."""
    from harness.resource_allocator import ResourceAllocator

    allocator = ResourceAllocator({})
    assert allocator.workload_weight == 0.3
    allocator.update_config({"resource_weight": 0.7})
    assert allocator.workload_weight == 0.7


# ------------------------------------------------------------------
# Result Validator tests
# ------------------------------------------------------------------


def test_result_validator_valid_result():
    """Test validation passes for a valid execution result."""
    from harness.result_validator import ResultValidator

    validator = ResultValidator({})
    result = validator.validate(
        {
            "tasks": [
                {"id": "t1", "status": "completed", "duration": 2.0},
                {"id": "t2", "status": "completed", "duration": 3.0},
            ],
            "total_duration": 5.0,
            "resource_usage": {"a1": 2.0, "a2": 3.0},
        }
    )
    assert result.is_valid is True
    assert len(result.violations) == 0


def test_result_validator_task_failure():
    """Test validation fails when a task did not complete."""
    from harness.result_validator import ResultValidator

    validator = ResultValidator({})
    result = validator.validate(
        {
            "tasks": [
                {"id": "t1", "status": "completed", "duration": 2.0},
                {"id": "t2", "status": "failed", "duration": 0.0},
            ],
            "total_duration": 2.0,
        }
    )
    assert result.is_valid is False
    assert len(result.violations) >= 1


# ------------------------------------------------------------------
# Exception Handler tests
# ------------------------------------------------------------------


def test_exception_handler_timeout():
    """Test timeout exception classification and retry recovery."""
    from harness.exception_handler import ExceptionHandler, ExceptionType

    handler = ExceptionHandler({})
    recovery = handler.handle(
        TimeoutError("Operation timed out"),
        {"task_id": "t1", "arm_id": "a1", "attempt": 1},
    )
    assert recovery.action_type.value == "retry"
    assert recovery.parameters["exception_type"] == "timeout"


def test_exception_handler_escalation():
    """Test retry escalates to REPLAN when max retries exceeded."""
    from harness.exception_handler import ExceptionHandler

    handler = ExceptionHandler({})
    # Default max retries for TIMEOUT is 3; attempt 3 should escalate
    recovery = handler.handle(
        TimeoutError("Timed out"),
        {"task_id": "t1", "arm_id": "a1", "attempt": 3},
    )
    assert recovery.action_type.value == "replan"


def test_exception_handler_update_config():
    """Test runtime config updates from feedback loop."""
    from harness.exception_handler import ExceptionHandler

    handler = ExceptionHandler({})
    old_retry = handler._max_retries
    handler.update_config({"retry_count": 10})
    for exc_type, count in handler._max_retries.items():
        assert count >= 10


# ------------------------------------------------------------------
# Feedback Loop tests
# ------------------------------------------------------------------


def test_feedback_loop_collect_and_analyze():
    """Test feedback collection and analysis."""
    from harness.feedback_loop import FeedbackLoop

    loop = FeedbackLoop({})
    for i in range(5):
        loop.collect_feedback(
            {
                "task_id": f"t{i}",
                "arm_id": "a1",
                "status": "success",
                "duration": 2.0 + i * 0.5,
                "resource_usage": {"a1": 2.0},
                "errors": [],
            }
        )
    analysis = loop.analyze_feedback()
    assert analysis.performance_score > 0.0
    assert isinstance(analysis.bottlenecks, list)
    assert isinstance(analysis.recommendations, list)


def test_feedback_loop_adjust_strategy():
    """Test strategy adjustments based on poor performance."""
    from harness.feedback_loop import FeedbackLoop

    loop = FeedbackLoop({})
    # Inject mostly failures to trigger adjustments
    for i in range(10):
        loop.collect_feedback(
            {
                "task_id": f"t{i % 3}",
                "arm_id": "a1",
                "status": "failure",
                "duration": 0.0,
                "resource_usage": {},
                "errors": ["timeout"],
            }
        )
    analysis = loop.analyze_feedback()
    adjustments = loop.adjust_strategy(analysis)
    # Should produce at least timeout and retry adjustments
    assert len(adjustments) >= 1
    strategy = loop.get_current_strategy()
    assert "retry_count" in strategy


def test_feedback_loop_code_gen_adjustment():
    """Test that feedback loop adjusts code generation parameters on failures."""
    from harness.feedback_loop import FeedbackLoop

    loop = FeedbackLoop({})
    # Mix of successes and failures (>20% failure rate)
    for i in range(3):
        loop.collect_feedback(
            {
                "task_id": f"ok{i}",
                "arm_id": "a1",
                "status": "success",
                "duration": 2.0,
                "resource_usage": {},
                "errors": [],
            }
        )
    for i in range(3):
        loop.collect_feedback(
            {
                "task_id": f"fail{i}",
                "arm_id": "a1",
                "status": "failure",
                "duration": 0.0,
                "resource_usage": {},
                "errors": ["execution error"],
            }
        )

    analysis = loop.analyze_feedback()
    adjustments = loop.adjust_strategy(analysis)

    code_gen_adjs = [a for a in adjustments if a.target_module == "code_generator"]
    assert len(code_gen_adjs) >= 1, "Expected code_generator adjustments"

    strategy = loop.get_current_strategy()
    assert strategy["code_gen_speed_factor"] < 1.0
    assert strategy["code_gen_force_factor"] > 1.0


def test_code_generator_update_config():
    """Test CodeGenerator accepts feedback-driven config updates."""
    from agent.code_generator import CodeGenerator

    gen = CodeGenerator({})
    assert gen.speed_factor == 1.0
    assert gen.force_factor == 1.0

    gen.update_config({"code_gen_speed_factor": 0.8})
    assert gen.speed_factor == 0.8

    gen.update_config({"code_gen_force_factor": 1.5})
    assert gen.force_factor == 1.5


def test_code_generator_speed_force_factors():
    """Test that speed_factor and force_factor affect generated code."""
    from agent.code_generator import CodeGenerator

    gen_default = CodeGenerator({})
    gen_slow = CodeGenerator({})
    gen_slow.update_config({"code_gen_speed_factor": 0.5, "code_gen_force_factor": 2.0})

    params = {"target_position": {"x": 1.0, "y": 0.5, "z": 0.3}}
    code_default = gen_default.generate(
        task_name="pick_test",
        task_description="pick",
        operation_type="pick",
        arm_id="a1",
        required_capabilities=["pick"],
        parameters=params,
    )
    code_slow = gen_slow.generate(
        task_name="pick_test",
        task_description="pick",
        operation_type="pick",
        arm_id="a1",
        required_capabilities=["pick"],
        parameters=params,
    )

    assert code_default.code != code_slow.code
    assert "speed=0.5" in code_default.code
    assert "speed=0.25" in code_slow.code
    assert "force=50.0" in code_default.code
    assert "force=100.0" in code_slow.code


def test_code_regeneration_on_failure():
    """Test that code is regenerated with adjusted factors after a task failure."""
    from agent.core import SchedulingAgent
    from simulation.mock_simulator import MockSimulator

    config = {
        "robot_arms": [
            {
                "id": "a1",
                "name": "A1",
                "capabilities": ["pick", "place", "move"],
            },
        ],
        "harness": {
            "feedback": {},
            "validation": {},
            "exception_handling": {},
        },
    }
    agent = SchedulingAgent(config)

    sim = MockSimulator(failure_probabilities={"pick": 1.0}, time_scale=1.0, seed=42)
    sim.initialize()
    sim.load_scene(
        {
            "robot_arms": [
                {"id": "a1", "position": {"x": 0, "y": 0, "z": 0}}
            ],
            "objects": [
                {
                    "id": "obj1",
                    "type": "workpiece",
                    "position": {"x": 1, "y": 0, "z": 0},
                }
            ],
        }
    )

    result = agent.execute_scheduling(
        instruction="Pick up workpiece",
        scene_config={
            "robot_arms": config["robot_arms"],
            "workpieces": [
                {
                    "id": "obj1",
                    "type": "part",
                    "initial_position": {"x": 1, "y": 0, "z": 0},
                }
            ],
        },
        simulation=sim,
    )

    assert agent.code_generator.speed_factor < 1.0
    assert agent.code_generator.force_factor > 1.0

    sim.close()


# ------------------------------------------------------------------
# Mock Simulator tests
# ------------------------------------------------------------------


def test_mock_simulator_execute_action():
    """Test mock simulator can execute a basic action."""
    from simulation.mock_simulator import MockSimulator

    sim = MockSimulator(time_scale=1.0, seed=42)
    sim.initialize()
    sim.load_scene(
        {
            "robot_arms": [{"id": "a1", "position": {"x": 0, "y": 0, "z": 0}}],
            "objects": [
                {
                    "id": "obj1",
                    "type": "workpiece",
                    "position": {"x": 1, "y": 0, "z": 0},
                }
            ],
        }
    )
    result = sim.execute_action(
        "a1", {"type": "move", "position": {"x": 1, "y": 0, "z": 0}}
    )
    assert result.success is True
    sim.close()


def test_mock_simulator_failure_injection():
    """Test mock simulator configurable failure rates."""
    from simulation.mock_simulator import MockSimulator

    # 100% failure rate for pick
    sim = MockSimulator(
        failure_probabilities={"pick": 1.0},
        time_scale=1.0,
        seed=42,
    )
    sim.initialize()
    sim.load_scene(
        {
            "robot_arms": [{"id": "a1", "position": {"x": 0, "y": 0, "z": 0}}],
            "objects": [
                {
                    "id": "obj1",
                    "type": "workpiece",
                    "position": {"x": 0, "y": 0, "z": 0},
                }
            ],
        }
    )
    result = sim.execute_action("a1", {"type": "pick", "target": "obj1"})
    assert result.success is False
    sim.close()


# ------------------------------------------------------------------
# End-to-end integration test
# ------------------------------------------------------------------


def test_full_pipeline_integration():
    """Test the complete pipeline runs end-to-end without errors."""
    from agent.core import SchedulingAgent

    config = {
        "robot_arms": [
            {
                "id": "arm_001",
                "name": "Arm1",
                "capabilities": ["pick", "place", "move", "assemble"],
            },
            {
                "id": "arm_002",
                "name": "Arm2",
                "capabilities": ["pick", "place", "move", "assemble"],
            },
        ],
        "harness": {
            "feedback": {},
            "validation": {},
            "exception_handling": {},
        },
        "simulation": {
            "backend": "mock",  # Use mock for unit tests (no GPU required)
        },
    }
    agent = SchedulingAgent(config)

    # Use instruction-based planning (no stations => _plan_from_instruction path)
    scene_config = {
        "robot_arms": config["robot_arms"],
        "workpieces": [
            {"id": "wp1", "type": "part", "initial_position": {"x": 0, "y": 0, "z": 0}},
        ],
    }

    result = agent.execute_scheduling(
        instruction="Pick up component, move to station, assemble and inspect",
        scene_config=scene_config,
    )

    assert result.execution_id is not None
    assert len(result.tasks) > 0
    assert result.makespan >= 0
    assert 0.0 <= result.task_success_rate <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
