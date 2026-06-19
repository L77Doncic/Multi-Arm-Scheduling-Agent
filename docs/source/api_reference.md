# API Reference

本页列出系统的核心类和函数接口。

## agent 模块

### SchedulingAgent

调度智能体主类，编排完整流水线。

```python
class SchedulingAgent:
    def __init__(self, config: Dict[str, Any]): ...

    def decompose_task(
        self,
        natural_language_instruction: str,
        scene_config: Optional[Dict] = None,
    ) -> List[Task]: ...

    def allocate_resources(self, tasks: List[Task]) -> Dict[str, str]: ...

    def generate_code(
        self,
        task: Task,
        arm: RobotArm,
        feedback: Optional[Dict] = None,
    ) -> str: ...

    def execute_scheduling(
        self,
        instruction: str,
        scene_config: Optional[Dict] = None,
        simulation=None,
    ) -> ExecutionResult: ...

    def get_performance_metrics(self) -> Dict[str, float]: ...
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
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
```

### TaskPlanner

```python
class TaskPlanner:
    def __init__(self, config: Dict, llm_client=None): ...

    def create_plan(
        self,
        instruction: str,
        scene_config: Optional[Dict] = None,
    ) -> TaskPlan: ...
```

### TaskPlan

```python
@dataclass
class TaskPlan:
    plan_id: str
    instruction: str
    tasks: List[TaskNode]
    dependency_graph: Dict[str, List[str]]
    estimated_makespan: float

    def get_execution_order(self) -> List[List[str]]: ...
    def get_task_by_id(self, task_id: str) -> Optional[TaskNode]: ...
```

### CodeGenerator

```python
class CodeGenerator:
    def __init__(self, config: Dict, llm_client=None): ...

    def generate(
        self,
        task_name: str,
        task_description: str,
        operation_type: str,
        arm_id: str,
        required_capabilities: List[str],
        parameters: Optional[Dict] = None,
        feedback: Optional[Dict] = None,
    ) -> GeneratedCode: ...
```

### GeneratedCode

```python
@dataclass
class GeneratedCode:
    task_id: str
    arm_id: str
    code: str
    imports: List[str]
    primitives_used: List[str]
    estimated_duration: float
```

## harness 模块

### TaskDecomposer

```python
class TaskDecomposer:
    def __init__(self, config: Dict): ...
    def decompose(self, instruction: str) -> List[DecomposedTask]: ...
```

### ResourceAllocator

```python
class ResourceAllocator:
    def __init__(self, config: Dict): ...
    def allocate(self, tasks: List[Dict], arms: List[Dict]) -> Dict[str, str]: ...
    def resolve_conflicts(self, conflicts, tasks, arms) -> Dict[str, str]: ...
```

### ResultValidator

```python
class ResultValidator:
    def __init__(self, config: Dict): ...
    def validate(self, execution_result, constraints) -> ValidationResult: ...
```

### ExceptionHandler

```python
class ExceptionHandler:
    def __init__(self, config: Dict): ...
    def handle(self, exception, context) -> RecoveryAction: ...
    def get_statistics(self) -> Dict: ...
```

### FeedbackLoop

```python
class FeedbackLoop:
    def __init__(self, config: Dict): ...
    def collect_feedback(self, execution_result) -> FeedbackData: ...
    def analyze_feedback(self, feedback) -> AnalysisResult: ...
    def adjust_strategy(self, analysis) -> StrategyAdjustment: ...
    def get_adjustment_history(self) -> List[StrategyAdjustment]: ...
```

## simulation 模块

### SimulationInterface (ABC)

```python
class SimulationInterface(ABC):
    def initialize(self) -> None: ...
    def load_scene(self, scene_config: dict) -> None: ...
    def execute_action(self, arm_id: str, action: dict) -> ActionResult: ...
    def get_state(self) -> SimulationState: ...
    def step(self) -> None: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...
```

### MockSimulator

```python
class MockSimulator(SimulationInterface):
    def __init__(
        self,
        failure_probabilities: Optional[Dict[str, float]] = None,
        action_durations: Optional[Dict[str, float]] = None,
        time_scale: float = 1.0,
        seed: Optional[int] = None,
    ): ...
```

### SceneBuilder

```python
class SceneBuilder:
    def build_from_config(self, config: dict) -> Scene: ...
    def build_assembly_line(
        self,
        num_stations: int,
        num_workpieces: int,
        num_arms: int,
    ) -> Scene: ...
```

## evaluation 模块

### MetricsCalculator

```python
class MetricsCalculator:
    def calculate_makespan(self, execution_log) -> float: ...
    def calculate_task_success_rate(self, execution_log) -> float: ...
    def calculate_resource_utilization(self, execution_log, num_arms) -> float: ...
    def calculate_constraint_violations(self, execution_log) -> int: ...
    def calculate_all(self, execution_log, num_arms) -> EvaluationMetrics: ...
```

### BenchmarkRunner

```python
class BenchmarkRunner:
    def load_dataset(self, dataset_path: str) -> List[Scenario]: ...
    def run_benchmark(self, agent, scenarios) -> BenchmarkResult: ...
    def compare_with_baseline(self, results, baseline) -> ComparisonReport: ...
    def generate_baseline_schedule(self, scenarios, method: str) -> List[Dict]: ...
```

### Visualizer

```python
class Visualizer:
    def plot_gantt_chart(self, execution_log, save_path: str) -> None: ...
    def plot_resource_utilization(self, execution_log, save_path: str) -> None: ...
    def plot_comparison(self, agent_metrics, baseline_metrics, save_path: str) -> None: ...
    def generate_html_report(self, results, save_path: str) -> None: ...
```

## LLM Clients

### LLMClient (ABC)

```python
class LLMClient(ABC):
    def generate(self, prompt: str, **kwargs) -> str: ...
    def generate_structured(self, prompt: str, schema: dict, **kwargs) -> dict: ...
    def count_tokens(self, text: str) -> int: ...
    def get_model_name(self) -> str: ...
```

### 工厂函数

```python
from agent.llm_clients.factory import create_llm_client

client = create_llm_client({
    "provider": "openai",
    "model": "gpt-4-turbo",
    "api_key": "sk-...",
})
```
