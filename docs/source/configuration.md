# Configuration

系统通过YAML配置文件控制行为。所有配置文件位于 `configs/` 目录。

## agent_config.yaml

主配置文件，控制智能体、LLM、机械臂和Harness。

```yaml
# LLM配置
llm:
  provider: "openai"          # openai / anthropic / local
  model: "gpt-4-turbo"
  api_base: "https://api.openai.com/v1"
  api_key_env: "OPENAI_API_KEY"
  temperature: 0.7
  max_tokens: 4096
  max_retries: 3
  retry_delay: 1.0

# 机械臂定义
robot_arms:
  - id: "arm_001"
    name: "Left Arm"
    type: "6-DOF"
    capabilities: ["pick", "place", "move", "assemble", "gripper", "force_control"]
    workspace:
      x_min: -1.0
      x_max: 1.0
      y_min: -1.0
      y_max: 1.0
      z_min: 0.0
      z_max: 2.0
    max_payload: 5.0
    max_speed: 2.0

  - id: "arm_002"
    name: "Right Arm"
    capabilities: ["pick", "place", "move", "assemble", "tighten", "gripper"]

  - id: "arm_003"
    name: "Top Arm"
    capabilities: ["pick", "place", "inspect", "vision"]

# 任务配置
task:
  max_subtasks: 20
  default_timeout: 30.0
  parallel_execution: true
  max_concurrent_tasks: 3

# Harness配置
harness:
  feedback:
    enabled: true
    interval: 1.0
    metrics: ["task_status", "resource_utilization", "error_rate"]
  validation:
    enabled: true
    strict_mode: false
    auto_retry: true
    max_retries: 3
  exception_handling:
    enabled: true
    log_errors: true
    recovery_strategies: ["retry", "skip", "fallback"]
```

### LLM配置详解

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | str | `"local"` | LLM提供商：`openai` / `anthropic` / `local` |
| `model` | str | — | 模型名称 |
| `temperature` | float | 0.7 | 生成温度 |
| `max_tokens` | int | 4096 | 最大输出token |
| `max_retries` | int | 3 | API调用重试次数 |
| `retry_delay` | float | 1.0 | 重试间隔（秒） |

!!! tip
    `provider: "local"` 或不配置LLM时，系统使用启发式模式。所有功能可用，无需API密钥。

### 机械臂配置详解

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | str | 唯一标识 |
| `name` | str | 显示名称 |
| `capabilities` | List[str] | 能力列表，用于任务匹配 |
| `workspace` | dict | 工作空间边界 |
| `max_payload` | float | 最大负载（kg） |
| `max_speed` | float | 最大速度（m/s） |

## simulation_config.yaml

仿真配置。

```yaml
simulation:
  backend: "mock"           # mock / isaac

  mock:
    failure_probability: 0.05
    record_trace: true
    time_acceleration: 100.0

  isaac_sim:
    headless: true
    device: "cuda:0"

  execution:
    max_steps: 10000
    timeout: 300.0
```

## evaluation_config.yaml

评估配置。

```yaml
evaluation:
  metrics:
    - makespan
    - task_success_rate
    - resource_utilization
    - constraint_violations

  baselines:
    - name: "random"
    - name: "greedy"
    - name: "optimal"

  statistics:
    confidence_level: 0.95
    num_runs: 5

  visualization:
    generate_gantt: true
    generate_comparison_chart: true
    generate_html_report: true
```

## 场景配置

场景定义在 `data/scenarios/` 的YAML文件中。

```yaml
scenario:
  name: "4-Station Assembly Line"

  stations:
    - id: "station_1"
      name: "Pick & Load"
      position: { x: 0.0, y: 0.0, z: 0.0 }
      capabilities_required: ["pick", "place"]
      operation: "pick_workpiece_from_feed"
      estimated_duration: 3.0
      predecessors: []
      successors: ["station_2"]

  workpieces:
    - id: "wp_A"
      type: "assembly_part_A"
      initial_position: { x: -1.0, y: -0.5, z: 0.5 }
      operations_sequence: ["station_1", "station_2", "station_3", "station_4"]
      priority: 1

  robot_arms:
    - id: "arm_001"
      capabilities: ["pick", "place", "move", "assemble", "gripper"]

  constraints:
    - type: "temporal"
      description: "Sequential station visits per workpiece"
      hard: true
    - type: "resource"
      description: "One workpiece per arm at a time"
      hard: true
    - type: "spatial"
      min_separation: 0.3
      hard: true

  instruction: >
    Two workpieces need to be assembled on a 4-station line.
    Coordinate three arms to minimize completion time.

  optimal_schedule:
    source: "MRTA-Benchmark"
    method: "MILP-optimal"
    makespan: 42.0
```

## 环境变量

| 变量 | 用途 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 |
| `ANTHROPIC_API_KEY` | Anthropic API密钥 |
