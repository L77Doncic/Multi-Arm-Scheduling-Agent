"""
Comprehensive unit tests for Multi-Arm Scheduling Agent
"""

import pytest
import sys
import os
import time
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# ============================================================
# Agent Core Tests
# ============================================================

class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_values(self):
        from agent.core import TaskStatus
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_all_statuses_exist(self):
        from agent.core import TaskStatus
        assert len(TaskStatus) == 5


class TestTask:
    """Test Task data class."""

    def test_creation(self):
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
        assert task.start_time is None

    def test_with_dependencies(self):
        from agent.core import Task
        task = Task(
            id="task_002",
            name="Assemble",
            description="Assemble components",
            dependencies=["task_001"],
        )
        assert "task_001" in task.dependencies

    def test_with_capabilities(self):
        from agent.core import Task
        task = Task(
            id="task_003",
            name="Weld",
            description="Weld joints",
            dependencies=[],
            operation_type="weld",
            required_capabilities=["weld", "positioning"],
        )
        assert "weld" in task.required_capabilities


class TestRobotArm:
    """Test RobotArm data class."""

    def test_creation(self):
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
        assert arm.total_busy_time == 0.0

    def test_defaults(self):
        from agent.core import RobotArm
        arm = RobotArm(id="a1", name="A1", capabilities=[])
        assert arm.current_task is None
        assert arm.task_history == []


class TestSchedulingAgent:
    """Test SchedulingAgent core functionality."""

    @pytest.fixture
    def agent(self):
        from agent.core import SchedulingAgent
        config = {
            'robot_arms': [
                {'id': 'arm_001', 'name': 'Left Arm', 'capabilities': ['pick', 'place', 'move', 'assemble']},
                {'id': 'arm_002', 'name': 'Right Arm', 'capabilities': ['pick', 'place', 'move', 'assemble', 'tighten']},
                {'id': 'arm_003', 'name': 'Top Arm', 'capabilities': ['pick', 'place', 'inspect']},
            ],
            'llm': {'provider': 'local'},
            'task': {'default_timeout': 30.0, 'max_concurrent_tasks': 3},
            'harness': {'validation': {'max_retries': 2}},
        }
        return SchedulingAgent(config)

    def test_initialization(self, agent):
        assert len(agent.robot_arms) == 3
        assert 'arm_001' in agent.robot_arms
        assert 'arm_002' in agent.robot_arms
        assert 'arm_003' in agent.robot_arms

    def test_decompose_with_scene(self, agent):
        scene_config = {
            'stations': [
                {'id': 's1', 'name': 'Pick', 'capabilities_required': ['pick'],
                 'operation': 'pick', 'estimated_duration': 2.0, 'predecessors': [], 'successors': ['s2']},
                {'id': 's2', 'name': 'Assemble', 'capabilities_required': ['assemble'],
                 'operation': 'assemble', 'estimated_duration': 5.0, 'predecessors': ['s1'], 'successors': []},
            ],
            'workpieces': [
                {'id': 'wp_A', 'operations_sequence': ['s1', 's2'], 'priority': 1},
            ],
        }
        tasks = agent.decompose_task("Assemble component A", scene_config)
        assert len(tasks) >= 2
        assert any(t.operation_type == 'pick' for t in tasks)
        assert any(t.operation_type == 'assemble' for t in tasks)

    def test_decompose_from_instruction(self, agent):
        tasks = agent.decompose_task("Pick up the part and place it on the table, then inspect it")
        assert len(tasks) >= 2

    def test_allocate_resources(self, agent):
        # Create tasks
        tasks = agent.decompose_task("Pick and place and inspect the component")
        allocation = agent.allocate_resources(tasks)
        assert len(allocation) >= 1
        # All allocated arms should exist
        for arm_id in allocation.values():
            assert arm_id in agent.robot_arms

    def test_generate_code(self, agent):
        from agent.core import Task, RobotArm
        task = Task(
            id="t1", name="pick_wp", description="Pick workpiece",
            dependencies=[], operation_type="pick",
            required_capabilities=["pick"], estimated_duration=2.0,
        )
        arm = agent.robot_arms['arm_001']
        code = agent.generate_code(task, arm)
        assert "move_to" in code
        assert "grip" in code
        assert "def execute_pick_wp" in code

    def test_generate_code_assemble(self, agent):
        from agent.core import Task
        task = Task(
            id="t2", name="assemble_wp", description="Assemble workpiece",
            dependencies=[], operation_type="assemble",
            required_capabilities=["assemble"], estimated_duration=8.0,
        )
        arm = agent.robot_arms['arm_001']
        code = agent.generate_code(task, arm)
        assert "set_compliance" in code
        assert "check_sensor" in code

    def test_execute_scheduling(self, agent):
        scene_config = {
            'stations': [
                {'id': 's1', 'name': 'Pick', 'capabilities_required': ['pick'],
                 'operation': 'pick', 'estimated_duration': 2.0, 'predecessors': [], 'successors': ['s2']},
                {'id': 's2', 'name': 'Place', 'capabilities_required': ['place'],
                 'operation': 'place', 'estimated_duration': 2.0, 'predecessors': ['s1'], 'successors': []},
            ],
            'workpieces': [
                {'id': 'wp_A', 'operations_sequence': ['s1', 's2'], 'priority': 1},
            ],
        }
        result = agent.execute_scheduling(
            instruction="Pick and place component A",
            scene_config=scene_config,
        )
        assert result.execution_id is not None
        assert len(result.tasks) >= 2
        assert result.makespan > 0
        assert 0 <= result.task_success_rate <= 1.0
        assert len(result.execution_log) >= 1

    def test_performance_metrics_empty(self, agent):
        metrics = agent.get_performance_metrics()
        assert metrics['total_executions'] == 0

    def test_performance_metrics_after_execution(self, agent):
        agent.execute_scheduling("Pick and place the component")
        metrics = agent.get_performance_metrics()
        assert metrics['total_executions'] == 1
        assert metrics['average_makespan'] > 0


# ============================================================
# Task Planner Tests
# ============================================================

class TestTaskPlanner:
    """Test TaskPlanner."""

    @pytest.fixture
    def planner(self):
        from agent.planner import TaskPlanner
        return TaskPlanner({})

    def test_create_plan_from_instruction(self, planner):
        plan = planner.create_plan("Pick up the part and assemble it")
        assert plan.plan_id is not None
        assert len(plan.tasks) >= 1
        assert plan.estimated_makespan > 0

    def test_create_plan_from_scene(self, planner):
        scene = {
            'stations': [
                {'id': 's1', 'operation': 'pick', 'capabilities_required': ['pick'],
                 'estimated_duration': 2.0, 'predecessors': [], 'successors': ['s2']},
                {'id': 's2', 'operation': 'assemble', 'capabilities_required': ['assemble'],
                 'estimated_duration': 5.0, 'predecessors': ['s1'], 'successors': []},
            ],
            'workpieces': [
                {'id': 'wp1', 'operations_sequence': ['s1', 's2']},
            ],
        }
        plan = planner.create_plan("Assemble workpiece", scene)
        assert len(plan.tasks) >= 2

    def test_execution_order(self, planner):
        scene = {
            'stations': [
                {'id': 's1', 'operation': 'pick', 'capabilities_required': ['pick'],
                 'estimated_duration': 2.0, 'predecessors': [], 'successors': ['s2']},
                {'id': 's2', 'operation': 'assemble', 'capabilities_required': ['assemble'],
                 'estimated_duration': 5.0, 'predecessors': ['s1'], 'successors': ['s3']},
                {'id': 's3', 'operation': 'inspect', 'capabilities_required': ['inspect'],
                 'estimated_duration': 3.0, 'predecessors': ['s2'], 'successors': []},
            ],
            'workpieces': [
                {'id': 'wp1', 'operations_sequence': ['s1', 's2', 's3']},
            ],
        }
        plan = planner.create_plan("Process workpiece", scene)
        order = plan.get_execution_order()
        assert len(order) >= 3  # 3 sequential levels
        # First level should be pick (no deps)
        assert any('pick' in plan.get_task_by_id(tid).operation_type for tid in order[0])

    def test_makespan_estimation(self, planner):
        scene = {
            'stations': [
                {'id': 's1', 'operation': 'pick', 'capabilities_required': ['pick'],
                 'estimated_duration': 2.0, 'predecessors': [], 'successors': ['s2']},
                {'id': 's2', 'operation': 'assemble', 'capabilities_required': ['assemble'],
                 'estimated_duration': 5.0, 'predecessors': ['s1'], 'successors': []},
            ],
            'workpieces': [
                {'id': 'wp1', 'operations_sequence': ['s1', 's2']},
            ],
        }
        plan = planner.create_plan("Process", scene)
        assert plan.estimated_makespan == pytest.approx(7.0, abs=0.1)


# ============================================================
# Code Generator Tests
# ============================================================

class TestCodeGenerator:
    """Test CodeGenerator."""

    @pytest.fixture
    def generator(self):
        from agent.code_generator import CodeGenerator
        return CodeGenerator({})

    def test_generate_pick(self, generator):
        result = generator.generate(
            task_name="pick_wp",
            task_description="Pick workpiece",
            operation_type="pick",
            arm_id="arm_001",
            required_capabilities=["pick"],
        )
        assert "move_to" in result.code
        assert "grip" in result.code
        assert "move_to" in result.primitives_used
        assert "grip" in result.primitives_used

    def test_generate_assemble(self, generator):
        result = generator.generate(
            task_name="assemble_wp",
            task_description="Assemble components",
            operation_type="assemble",
            arm_id="arm_001",
            required_capabilities=["assemble"],
        )
        assert "set_compliance" in result.code
        assert "check_sensor" in result.code

    def test_generate_inspect(self, generator):
        result = generator.generate(
            task_name="inspect_wp",
            task_description="Inspect quality",
            operation_type="inspect",
            arm_id="arm_003",
            required_capabilities=["inspect"],
        )
        assert "check_sensor('vision')" in result.code

    def test_generate_weld(self, generator):
        result = generator.generate(
            task_name="weld_joint",
            task_description="Weld joints",
            operation_type="weld",
            arm_id="arm_002",
            required_capabilities=["weld"],
        )
        assert "weld_trigger" in result.code

    def test_generate_package(self, generator):
        result = generator.generate(
            task_name="package_wp",
            task_description="Package output",
            operation_type="package",
            arm_id="arm_001",
            required_capabilities=["pick", "place"],
        )
        assert "release" in result.code

    def test_primitives_detected(self, generator):
        result = generator.generate(
            task_name="test",
            task_description="test",
            operation_type="pick",
            arm_id="arm_001",
            required_capabilities=["pick"],
        )
        assert "move_to" in result.primitives_used
        assert "grip" in result.primitives_used
        assert "linear_move" in result.primitives_used

    def test_code_has_imports(self, generator):
        result = generator.generate(
            task_name="test",
            task_description="test",
            operation_type="pick",
            arm_id="arm_001",
            required_capabilities=["pick"],
        )
        assert "import time" in result.code

    def test_code_is_valid_python(self, generator):
        result = generator.generate(
            task_name="test_task",
            task_description="Test operation",
            operation_type="pick",
            arm_id="arm_001",
            required_capabilities=["pick"],
        )
        # Should compile without syntax errors
        compile(result.code, '<generated>', 'exec')


# ============================================================
# Scenario Data Tests
# ============================================================

class TestScenarioData:
    """Test scenario data files."""

    def test_assembly_line_loads(self):
        import yaml
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scenarios', 'assembly_line_4station.yaml')
        if not os.path.exists(path):
            pytest.skip("Scenario file not found")
        with open(path) as f:
            data = yaml.safe_load(f)
        scenario = data['scenario']
        assert len(scenario['stations']) >= 4
        assert len(scenario['workpieces']) >= 2
        assert len(scenario['robot_arms']) >= 2
        assert 'instruction' in scenario

    def test_complex_assembly_loads(self):
        import yaml
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'scenarios', 'complex_assembly.yaml')
        if not os.path.exists(path):
            pytest.skip("Scenario file not found")
        with open(path) as f:
            data = yaml.safe_load(f)
        scenario = data['scenario']
        assert len(scenario['stations']) >= 5
        assert len(scenario['workpieces']) >= 3

    def test_mrta_benchmark_loads(self):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'datasets', 'mrta_benchmark.json')
        if not os.path.exists(path):
            pytest.skip("Dataset file not found")
        with open(path) as f:
            data = json.load(f)
        assert data['dataset'] == 'MRTA-Benchmark'
        assert len(data['scenarios']) >= 3

    def test_mrta_scenario_has_optimal(self):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'datasets', 'mrta_benchmark.json')
        if not os.path.exists(path):
            pytest.skip("Dataset file not found")
        with open(path) as f:
            data = json.load(f)
        for scenario in data['scenarios']:
            assert 'optimal_makespan' in scenario
            assert scenario['optimal_makespan'] > 0


# ============================================================
# Config Tests
# ============================================================

class TestConfig:
    """Test configuration files."""

    def test_agent_config_loads(self):
        import yaml
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'agent_config.yaml')
        with open(path) as f:
            config = yaml.safe_load(f)
        assert 'llm' in config
        assert 'robot_arms' in config
        assert len(config['robot_arms']) >= 2

    def test_simulation_config_loads(self):
        import yaml
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'simulation_config.yaml')
        if not os.path.exists(path):
            pytest.skip("Config not found")
        with open(path) as f:
            config = yaml.safe_load(f)
        assert 'simulation' in config

    def test_evaluation_config_loads(self):
        import yaml
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'evaluation_config.yaml')
        if not os.path.exists(path):
            pytest.skip("Config not found")
        with open(path) as f:
            config = yaml.safe_load(f)
        assert 'evaluation' in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
