# Configuration

系统通过 YAML 配置文件控制行为。所有配置文件位于 `configs/` 目录。

## agent_config.yaml

主配置文件，控制智能体、LLM、机械臂和 Harness。

### LLM 配置

```yaml
llm:
  provider: "openai"                              # openai / anthropic
  model: "deepseek-ai/DeepSeek-V4-Flash"          # 模型名称
  api_base: "https://api-inference.modelscope.cn/v1"
  api_key_env: "OPENAI_API_KEY"                   # 从环境变量读取密钥
  temperature: 0.7
  max_tokens: 4096
  max_retries: 3
  retry_delay: 1.0
```

设置 API 密钥（二选一）：

```bash
# 方式一：环境变量
export OPENAI_API_KEY="your-api-key"

# 方式二：.env 文件
cp .env.example .env
# 编辑 .env 填入密钥
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | str | — | LLM 提供商 |
| `model` | str | — | 模型名称 |
| `api_base` | str | — | API 基础 URL |
| `api_key` | str | — | API 密钥 |
| `temperature` | float | 0.7 | 生成温度 |
| `max_tokens` | int | 4096 | 最大输出 token |
| `max_retries` | int | 3 | API 重试次数 |
| `retry_delay` | float | 1.0 | 重试间隔（秒） |

> [!TIP]
> 不配置 LLM 时，系统使用启发式模式。所有功能可用，无需 API 密钥。

### 机械臂配置

```yaml
robot_arms:
  - id: "arm_001"
    name: "Left Arm"
    type: "6-DOF"
    capabilities: ["pick", "place", "move", "assemble", "gripper", "force_control"]
    base_position: { x: 1.0, y: -1.5, z: 0.0 }
    max_payload: 5.0    # kg
    max_speed: 2.0      # m/s
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | str | 唯一标识 |
| `name` | str | 显示名称 |
| `capabilities` | List[str] | 能力列表，用于任务匹配 |
| `base_position` | dict | 基座位置 |
| `max_payload` | float | 最大负载（kg） |
| `max_speed` | float | 最大速度（m/s） |

### Harness 配置

```yaml
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
    notify_on_critical: true
    recovery_strategies: ["retry", "skip", "fallback"]
```

### 评估配置

```yaml
evaluation:
  metrics:
    - makespan
    - task_success_rate
    - resource_utilization
    - constraint_violations
  benchmark:
    enabled: true
    dataset: "MRTA-Benchmark"
    compare_with_baseline: true
```

## simulation_config.yaml

```yaml
simulation:
  backend: "mock"           # mock / isaac / omniverse / isaac_lab

  mock:
    failure_probability: 0.05
    record_trace: true
    time_acceleration: 1.0

  isaac_sim:
    headless: true
    device: "cuda:0"

  execution:
    max_steps: 10000
    timeout: 300.0
```

## 场景配置

场景定义在 `data/scenarios/` 的 YAML 文件中：

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
      base_position: { x: 1.0, y: -1.5, z: 0.0 }

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
    source: "MILP-optimal (constructed for this scenario)"
    method: "Mixed Integer Linear Programming"
    makespan: 25.0
```

## 环境变量

| 变量 | 用途 |
|------|------|
| `OPENAI_API_KEY` | LLM API 密钥（可替代配置文件中的 `api_key`） |
