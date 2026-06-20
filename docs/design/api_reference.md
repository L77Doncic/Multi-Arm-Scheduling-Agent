# API 参考文档

本文档列出系统所有核心类的公共 API。

## 目录

- [SchedulingAgent](#schedulingagent)
- [ExecutionResult](#executionresult)
- [SyncLLMClient](#syncllmclient)
- [TaskPlanner](#taskplanner)
- [CodeGenerator](#codegenerator)
- [ResourceAllocator](#resourceallocator)
- [FeedbackLoop](#feedbackloop)
- [ExceptionHandler](#exceptionhandler)
- [ResultValidator](#resultvalidator)
- [SimulationInterface](#simulationinterface)
- [ArmInterface](#arminterface)
- [MetricsCalculator](#metricscalculator)
- [MRTABenchmarkLoader](#mrtabenchmarkloader)

---

## SchedulingAgent

`agent.core.SchedulingAgent`

多机械臂调度智能体主类，编排完整 6 步调度管线。

### 构造函数

```python
SchedulingAgent(config: Dict[str, Any])
```

**参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `Dict[str, Any]` | 配置字典，包含 LLM 设置、机械臂定义、Harness 参数 |

**属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `robot_arms` | `Dict[str, RobotArm]` | 机械臂字典 |
| `llm_client` | `SyncLLMClient \| None` | LLM 客户端 |
| `planner` | `TaskPlanner` | 任务规划器 |
| `code_generator` | `CodeGenerator` | 代码生成器 |
| `resource_allocator` | `ResourceAllocator` | 资源分配器 |
| `feedback_loop` | `FeedbackLoop` | 闭环反馈 |
| `exception_handler` | `ExceptionHandler` | 异常处理 |
| `result_validator` | `ResultValidator` | 结果验证 |
| `execution_history` | `List[ExecutionResult]` | 历史执行记录 |

### 方法

#### `execute_scheduling(instruction, scene_config=None, simulation=None) -> ExecutionResult`

执行完整调度管线。

| 参数 | 类型 | 必需 | 说明 |
|------|------|:----:|------|
| `instruction` | `str` | ✅ | 自然语言指令 |
| `scene_config` | `dict` | ❌ | 场景配置 |
| `simulation` | `SimulationInterface` | ❌ | 仿真器，None 时自动创建 MockSimulator |

#### `get_performance_metrics() -> Dict[str, float]`

获取历史执行的平均指标。

---

## ExecutionResult

`agent.core.ExecutionResult`

完整调度执行结果。

```python
@dataclass
class ExecutionResult:
    execution_id: str                              # 执行唯一 ID
    instruction: str                               # 原始指令
    tasks: List[Task]                              # 所有任务
    allocation: Dict[str, str]                     # {task_id: arm_id}
    makespan: float                                # 总完工时间（秒）
    task_success_rate: float                       # 任务成功率 [0, 1]
    resource_utilization: float                    # 资源利用率 [0, 1]
    constraint_violations: int                     # 约束违反次数
    execution_log: List[Dict[str, Any]]            # 执行日志
    feedback_adjustments: List[Dict[str, Any]]     # 反馈策略调整
    generated_codes: Dict[str, str]                # {task_id: code_str}
```

---

## SyncLLMClient

`agent.llm_clients.sync_client.SyncLLMClient`

同步 LLM 客户端，兼容 OpenAI API。

### 构造函数

```python
SyncLLMClient(config: Dict[str, Any])
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `config.api_key` | `str` | API 密钥 |
| `config.api_base` | `str` | API 基础 URL |
| `config.model` | `str` | 模型名称 |
| `config.temperature` | `float` | 生成温度（默认 0.7） |
| `config.max_tokens` | `int` | 最大输出 token（默认 4096） |
| `config.max_retries` | `int` | 重试次数（默认 3） |

### 方法

#### `generate(prompt: str, **kwargs) -> str`

生成文本响应。

#### `generate_structured(prompt: str, schema: dict = None, **kwargs) -> Dict[str, Any]`

生成结构化 JSON 响应，自动提取和修复 JSON。

---

## TaskPlanner

`agent.planner.TaskPlanner`

任务规划器，支持 LLM 和启发式双路径。

### 构造函数

```python
TaskPlanner(config: Dict[str, Any], llm_client=None)
```

### 方法

#### `create_plan(instruction: str, scene_config: dict = None) -> TaskPlan`

创建任务计划。

**返回**: `TaskPlan`，包含 `tasks`, `dependency_graph`, `estimated_makespan`

#### `TaskPlan.get_execution_order() -> List[List[str]]`

返回拓扑排序的执行层级（同一层级可并行）。

---

## CodeGenerator

`agent.code_generator.CodeGenerator`

代码生成器，基于 9 个原子原语动态编排。

### 原子原语

| 原语 | 签名 | 描述 |
|------|------|------|
| `move_to` | `(x, y, z, speed=1.0)` | 移动到绝对位置 |
| `linear_move` | `(dx, dy, dz, speed=1.0)` | 相对位移 |
| `grip` | `(force=50.0)` | 闭合夹爪 |
| `release` | `()` | 张开夹爪 |
| `rotate` | `(roll, pitch, yaw, speed=1.0)` | 旋转末端执行器 |
| `wait` | `(duration=1.0)` | 等待 |
| `check_sensor` | `(sensor_type)` | 读取传感器（force/vision/proximity） |
| `set_payload` | `(mass=0.0)` | 设置负载质量 |
| `set_compliance` | `(stiffness_x, stiffness_y, stiffness_z)` | 设置柔顺性 |

### 方法

#### `generate(task_name, task_description, operation_type, arm_id, required_capabilities, parameters=None, feedback=None) -> GeneratedCode`

生成可执行代码。支持基于反馈的精炼。

| 参数 | 类型 | 说明 |
|------|------|------|
| `feedback` | `dict` | 上次执行的反馈，用于 LLM 精炼 |

---

## ResourceAllocator

`harness.resource_allocator.ResourceAllocator`

资源分配器，贪心 + 冲突检测 + 负载均衡。

### 方法

#### `allocate(tasks: List, robot_arms: List) -> Dict[str, str]`

分配任务到机械臂。返回 `{task_id: arm_id}`。

#### `resolve_conflicts(conflicts: List[Conflict], tasks: List, arms: List) -> Dict[str, str]`

解决检测到的冲突。

---

## FeedbackLoop

`harness.feedback_loop.FeedbackLoop`

闭环反馈机制。

### 方法

#### `collect_feedback(execution_result: dict) -> FeedbackData`

收集单次执行反馈。

#### `analyze_feedback(feedback: List[FeedbackData] = None) -> AnalysisResult`

分析反馈数据，返回性能评分、瓶颈、建议。

**返回**: `AnalysisResult {performance_score, bottlenecks, recommendations}`

#### `adjust_strategy(analysis: AnalysisResult = None) -> List[StrategyAdjustment]`

根据分析结果调整策略参数。

**返回**: `List[StrategyAdjustment]`，每个调整包含 `target_module`, `parameter`, `old_value`, `new_value`, `reason`

#### `get_current_strategy() -> Dict[str, float]`

获取当前策略参数。

---

## ExceptionHandler

`harness.exception_handler.ExceptionHandler`

异常处理，7 种异常分类 + 4 种恢复策略。

### 方法

#### `handle(exception: BaseException, context: dict) -> RecoveryAction`

分类异常并确定恢复动作。

#### `get_statistics() -> Dict[str, Any]`

返回异常统计（按类型计数、成功率等）。

---

## ResultValidator

`harness.result_validator.ResultValidator`

结果验证，时间/空间/资源约束检查。

### 方法

#### `validate(execution_result: dict, constraints: List[Constraint] = None) -> ValidationResult`

验证执行结果。返回 `ValidationResult {is_valid, violations, metrics, summary}`。

---

## SimulationInterface

`simulation.base.SimulationInterface`

抽象仿真接口，所有后端必须实现。

### 抽象方法

| 方法 | 说明 |
|------|------|
| `initialize()` | 初始化仿真环境 |
| `load_scene(scene_config: dict)` | 加载场景 |
| `execute_action(arm_id: str, action: dict) -> ActionResult` | 执行动作 |
| `get_state() -> SimulationState` | 获取当前状态 |
| `step()` | 前进一个时间步 |
| `reset()` | 重置仿真 |
| `close()` | 关闭仿真 |

### 实现类

| 类 | 后端 | GPU 需求 |
|----|------|:--------:|
| `MockSimulator` | 纯 Python | ❌ |
| `IsaacSimInterface` | Isaac Sim | ✅ |
| `OmniverseInterface` | Omniverse | ✅ |
| `IsaacLabInterface` | Isaac Lab | ✅ |

所有 GPU 后端支持 `fallback_to_mock=True`，未安装时自动回退。

---

## ArmInterface

`simulation.arm_interface.ArmInterface`

原子原语到仿真动作的适配器。

### 构造函数

```python
ArmInterface(arm_id: str, simulation: SimulationInterface, estimated_duration: float = 3.0)
```

### 原语方法

`move_to()`, `linear_move()`, `grip()`, `release()`, `rotate()`, `wait()`, `check_sensor()`, `set_payload()`, `set_compliance()`

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `total_duration` | `float` | 总仿真时长 |
| `action_count` | `int` | 原语调用次数 |
| `errors` | `list` | 错误列表 |
| `success` | `bool` | 是否无错误 |

### 模块函数

#### `execute_generated_code(code_str, arm_id, simulation, estimated_duration) -> dict`

执行生成的 Python 代码字符串，返回执行结果字典。

---

## MetricsCalculator

`evaluation.metrics.MetricsCalculator`

评估指标计算器。

### 方法

#### `calculate_all(execution_log: ExecutionLog, num_arms: int) -> EvaluationMetrics`

计算所有指标。

**返回**: `EvaluationMetrics {makespan, task_success_rate, resource_utilization, constraint_violations, total_tasks, completed_tasks, failed_tasks}`

#### `calculate_makespan(execution_log) -> float`

#### `calculate_task_success_rate(execution_log) -> float`

#### `calculate_resource_utilization(execution_log, num_arms) -> float`

#### `calculate_constraint_violations(execution_log) -> int`

---

## MRTABenchmarkLoader

`evaluation.mrta_loader.MRTABenchmarkLoader`

APEX-MR 数据集加载器。

### 构造函数

```python
MRTABenchmarkLoader(data_dir: str)
```

### 方法

#### `load_all() -> List[MRTATask]`

加载所有任务。

#### `load_task(task_name: str) -> MRTATask`

加载单个任务。

#### `task_to_scenario_config(task: MRTATask, num_arms: int = 2) -> dict`

将 APEX-MR 任务转换为场景配置。

### 模块函数

#### `get_optimal_makespans() -> Dict[str, float]`

获取 APEX-MR 论文报告的最优 makespan。

**返回**: `{task_name: makespan_seconds}`，共 13 个任务。
