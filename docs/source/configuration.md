# Configuration

系统通过 YAML 配置文件控制行为。所有配置文件位于 `configs/` 目录。

## agent_config.yaml

主配置文件，控制智能体、LLM、机械臂和 Harness。

### LLM 配置

```yaml
llm:
  provider: "openai"                              # openai / anthropic
  model: "mimo-v2.5"                              # 模型名称
  api_base: "https://token-plan-cn.xiaomimimo.com/v1"
  api_key_env: "OPENAI_API_KEY"                   # 从环境变量读取密钥
  temperature: 0.7
  top_p: 0.9
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
  backend: "isaac"           # isaac (Isaac Sim 4.5)

  physics:
    timestep: 0.01
    gravity: [0, 0, -9.81]
    solver_iterations: 10

  isaac_sim:
    headless: true
    device: "cuda:0"

  scene:
    bounds:
      x_min: -5.0
      x_max: 10.0
      y_min: -5.0
      y_max: 5.0
      z_min: 0.0
      z_max: 5.0
    lighting:
      type: "dome"
      intensity: 1000

  execution:
    max_steps: 10000
    timeout: 300.0
    real_time_factor: 0.0
```

## 场景配置

场景定义在 `data/scenarios/` 的 JSON 文件中：

```json
{
  "scenario": {
    "name": "MRTA-1p-ProductionLine",
    "instruction": "Execute a 4-station production line with 2 workpieces...",
    "stations": [
      {
        "id": "station_feed",
        "name": "Feed Station",
        "position": {"x": 0, "y": 0, "z": 0},
        "capabilities_required": ["pick"],
        "operation": "feed"
      }
    ],
    "workpieces": [
      {
        "id": "workpiece_1",
        "type": "generic",
        "initial_position": {"x": 0, "y": 0, "z": 0.5}
      }
    ],
    "robot_arms": [
      {
        "id": "arm_001",
        "capabilities": ["pick", "place", "move"],
        "base_position": {"x": 1.0, "y": 0, "z": 0}
      }
    ],
    "optimal_schedule": {
      "makespan": 584.9
    }
  }
}
```

可用场景（基于MRTA-Benchmark格式）：

| 场景文件 | 说明 | 最优Makespan |
|----------|------|:------------:|
| 1p_production_line.json | 1工件，4工位，3机械臂 | 584.9s |
| 2p_production_line.json | 2工件，4工位，3机械臂 | 931.0s |
| 3p_production_line.json | 3工件，4工位，3机械臂 | 642.8s |
| 4p_production_line.json | 4工件，4工位，3机械臂 | 465.0s |
| 5p_production_line.json | 5工件，4工位，3机械臂 | 490.9s |
| 6p_production_line.json | 6工件，4工位，3机械臂 | 489.8s |

## 环境变量

| 变量 | 用途 |
|------|------|
| `OPENAI_API_KEY` | LLM API 密钥（可替代配置文件中的 `api_key`） |
