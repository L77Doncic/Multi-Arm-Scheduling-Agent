# Harness Engineering 框架设计文档

## 1. 概述

Harness Engineering 框架是多机械臂调度智能体的核心约束框架，负责确保调度系统的可靠性、可追溯性和自适应性。框架采用闭环反馈机制，将仿真执行结果实时回传至调度引擎，实现策略的动态调整。

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    LLM 智能体核心                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐          │
│  │ 任务规划器 │  │ 资源分配器 │  │  代码生成器   │          │
│  └─────┬────┘  └─────┬────┘  └──────┬───────┘          │
│        │             │              │                    │
│        ▼             ▼              ▼                    │
│  ┌─────────────────────────────────────────────┐        │
│  │              Harness 约束框架                 │        │
│  │  ┌────────────┐  ┌────────────┐  ┌────────┐ │        │
│  │  │ 任务分解器  │  │ 结果验证器  │  │异常处理 │ │        │
│  │  └─────┬──────┘  └─────┬──────┘  └───┬────┘ │        │
│  │        │               │             │      │        │
│  │        ▼               ▼             ▼      │        │
│  │  ┌──────────────────────────────────────┐   │        │
│  │  │          闭环反馈机制                 │   │        │
│  │  │  收集 → 分析 → 策略调整 → 重新调度   │   │        │
│  │  └──────────────────────────────────────┘   │        │
│  └─────────────────────────────────────────────┘        │
│                         │                                │
│                         ▼                                │
│  ┌─────────────────────────────────────────────┐        │
│  │              仿真执行层                      │        │
│  │  Isaac Sim / Omniverse / Mock Simulator     │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

## 3. 核心模块设计

### 3.1 任务分解器 (TaskDecomposer)

**职责**：将自然语言指令解析为结构化的子任务序列，建立任务依赖关系图。

**输入**：
- 自然语言指令（字符串）
- 场景配置（可选，包含工位、工件、机械臂定义）

**输出**：
- `List[DecomposedTask]` — 分解后的任务列表，每个任务包含：
  - `id`: 唯一标识
  - `name`: 任务名称
  - `operation_type`: 操作类型 (pick/place/assemble/inspect/...)
  - `dependencies`: 前置任务ID列表
  - `required_capabilities`: 所需能力列表
  - `estimated_duration`: 预估耗时

**算法**：
1. **模式匹配**：基于关键词识别操作类型（pick/grab → pick, assemble/connect → assemble）
2. **场景解析**：从场景配置中提取工位-工件操作序列
3. **依赖推断**：基于操作顺序和因果关系建立依赖图
4. **拓扑排序**：生成执行层级，支持并行执行

**LLM增强**（可选）：
- 使用结构化提示词让LLM分析指令语义
- 输出JSON格式的任务分解结果
- 失败时回退到启发式方法

### 3.2 资源分配器 (ResourceAllocator)

**职责**：将任务分配给最合适的机械臂，优化整体调度效率。

**分配策略**：
1. **能力匹配**：检查机械臂能力是否满足任务需求（权重70%）
2. **负载均衡**：优先分配给负载较低的机械臂（权重30%）
3. **冲突检测**：识别时间重叠和资源冲突
4. **冲突解决**：通过重新分配或调整时序解决冲突

**算法**：
```
for each task (按依赖层级排序):
    for each arm:
        score = capability_match * 0.7 + load_balance * 0.3
    assign task to arm with highest score
```

**数据结构**：
```python
@dataclass
class Conflict:
    task1_id: str
    task2_id: str
    arm_id: str
    conflict_type: str  # "temporal" | "resource" | "spatial"
```

### 3.3 结果验证器 (ResultValidator)

**职责**：验证仿真执行结果是否满足所有约束条件。

**验证维度**：
1. **任务完成度**：所有任务是否成功完成
2. **时间约束**：是否在规定时间内完成（makespan < max_makespan）
3. **资源约束**：机械臂是否超负载、是否发生碰撞
4. **空间约束**：机械臂间距是否满足最小安全距离

**输出**：
```python
@dataclass
class ValidationResult:
    is_valid: bool
    violations: List[Violation]  # 违反的约束列表
    metrics: Dict[str, float]    # 计算的性能指标
    summary: str                 # 验证摘要
```

### 3.4 异常处理器 (ExceptionHandler)

**职责**：检测异常、分类异常类型、确定恢复策略。

**异常类型**：
| 类型 | 描述 | 默认恢复策略 |
|------|------|-------------|
| TIMEOUT | 任务执行超时 | 重试 (retry) |
| RESOURCE_CONFLICT | 资源冲突 | 重新规划 (replan) |
| COLLISION | 碰撞检测 | 重试 + 调整路径 |
| SIMULATION_ERROR | 仿真异常 | 回退 (fallback) |
| CODE_GENERATION_ERROR | 代码生成失败 | 重试 + 模板回退 |
| CONSTRAINT_VIOLATION | 约束违反 | 跳过 (skip) 或重试 |

**恢复策略优先级**：retry > replan > fallback > skip

**统计追踪**：记录所有异常及其恢复结果，用于反馈分析。

### 3.5 闭环反馈机制 (FeedbackLoop)

**职责**：收集执行反馈、分析性能瓶颈、动态调整策略参数。

**反馈流程**：
```
仿真执行 → 结果采集 → 性能分析 → 策略调整 → 重新调度
    │           │           │           │           │
    └─── 成功/失败/超时 ───┘           │           │
                    └── 瓶颈识别 ──────┘           │
                              └── 参数更新 ────────┘
```

**可调参数**：
| 参数 | 模块 | 描述 |
|------|------|------|
| `default_timeout` | task | 任务默认超时时间 |
| `max_retries` | harness | 最大重试次数 |
| `resource_weight` | allocator | 资源分配权重 |
| `priority_boost` | planner | 优先级提升系数 |

**分析输出**：
```python
@dataclass
class AnalysisResult:
    performance_score: float          # 0.0 ~ 1.0
    bottlenecks: List[str]            # 瓶颈任务ID列表
    recommendations: List[str]        # 优化建议
```

## 4. 闭环反馈的数据流

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ 任务分解  │────▶│ 资源分配  │────▶│ 代码生成  │
└──────────┘     └──────────┘     └─────┬────┘
                                        │
                                        ▼
                                  ┌──────────┐
                                  │ 仿真执行  │
                                  └─────┬────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              ┌──────────┐       ┌──────────┐       ┌──────────┐
              │ 结果验证  │       │ 异常检测  │       │ 性能分析  │
              └─────┬────┘       └─────┬────┘       └─────┬────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                                  ┌──────────┐
                                  │ 策略调整  │
                                  └─────┬────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │ 更新调度参数      │
                              │ → 重新分解/分配   │
                              └──────────────────┘
```

## 5. 接口规范

### 5.1 Harness模块统一接口

所有Harness模块遵循统一的初始化和调用模式：

```python
class HarnessModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def process(self, input_data: Any) -> Any:
        """处理输入并返回结果"""
        raise NotImplementedError
```

### 5.2 反馈数据格式

```python
feedback = {
    'task_id': str,          # 任务ID
    'arm_id': str,           # 机械臂ID
    'status': str,           # completed/failed/timeout
    'duration': float,       # 执行耗时(秒)
    'result': dict,          # 执行结果详情
    'error': str | None,     # 错误信息
    'constraint_violation': bool,  # 是否违反约束
}
```

### 5.3 策略调整格式

```python
adjustment = {
    'target_module': str,    # 调整目标模块
    'parameter': str,        # 调整参数名
    'old_value': Any,        # 旧值
    'new_value': Any,        # 新值
    'reason': str,           # 调整原因
}
```

## 6. 配置说明

Harness框架通过 `configs/agent_config.yaml` 配置：

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
    recovery_strategies: ["retry", "skip", "fallback"]
```

## 7. 扩展指南

### 添加新的恢复策略

1. 在 `ExceptionHandler._determine_recovery()` 中添加新的策略分支
2. 在 `recovery_strategies` 配置中注册新策略
3. 在执行循环中处理新的恢复动作

### 添加新的验证维度

1. 在 `ResultValidator` 中添加新的 `_validate_*` 方法
2. 在 `validate()` 方法中调用新验证器
3. 定义新的 `Constraint` 类型

### 添加新的反馈指标

1. 在 `FeedbackLoop.collect_feedback()` 中采集新指标
2. 在 `analyze_feedback()` 中分析新指标
3. 在 `adjust_strategy()` 中定义相应的参数调整
