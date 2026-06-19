"""
Basic unit tests for Multi-Arm Scheduling Agent
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_import_agent():
    """Test that agent module can be imported."""
    from agent.core import SchedulingAgent, Task, RobotArm, TaskStatus
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
        status=TaskStatus.PENDING
    )
    assert task.id == "task_001"
    assert task.name == "Pick Component"
    assert task.status == TaskStatus.PENDING
    assert task.assigned_arm is None


def test_robot_arm_creation():
    """Test RobotArm data class creation."""
    from agent.core import RobotArm
    arm = RobotArm(
        id="arm_001",
        name="Left Arm",
        capabilities=["pick", "place", "move"]
    )
    assert arm.id == "arm_001"
    assert arm.name == "Left Arm"
    assert "pick" in arm.capabilities
    assert arm.is_busy is False


def test_scheduling_agent_initialization():
    """Test SchedulingAgent initialization."""
    from agent.core import SchedulingAgent
    config = {
        'robot_arms': [
            {
                'id': 'arm_001',
                'name': 'Test Arm',
                'capabilities': ['pick', 'place']
            }
        ]
    }
    agent = SchedulingAgent(config)
    assert len(agent.robot_arms) == 1
    assert 'arm_001' in agent.robot_arms


def test_task_decomposer_import():
    """Test that task decomposer module can be imported."""
    from harness.task_decomposer import TaskDecomposer, DecomposedTask
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
