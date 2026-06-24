# Harness Framework

Harness Engineering 是系统的约束框架，确保调度的可靠性、可追溯性和自适应性。它由5个模块组成，通过闭环反馈连接。

## 架构

```
┌─────────────────────────────────────────────────────┐
│                 Harness 约束框架                      │
│                                                     │
│  ┌──────────────┐      ┌──────────────┐            │
│  │TaskDecomposer│─────▶│   Resource   │            │
│  │  任务分解     │      │  Allocator   │            │
│  └──────────────┘      │  资源分配     │            │
│                        └──────┬───────┘            │
│                               │                     │
│  ┌──────────────┐      ┌──────▼───────┐            │
│  │  Exception   │◀─────│   Result     │            │
│  │  Handler     │      │  Validator   │            │
│  │  异常处理     │      │  结果验证     │            │
│  └──────┬───────┘      └──────────────┘            │
│         │                                           │
│  ┌──────▼───────┐                                   │
│  │  Feedback    │──── 策略调整 ────▶ 各模块          │
│  │  Loop        │                                   │
│  │  闭环反馈     │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

## 模块详解

### TaskDecomposer

将自然语言指令分解为结构化任务。详见 [Task Decomposition](tasks.md)。

### ResourceAllocator

将任务分配给机械臂。详见 [Scheduling](scheduling.md)。

### ResultValidator

验证执行结果是否满足约束。

```python
from harness.result_validator import ResultValidator, Constraint, ConstraintType, Severity

validator = ResultValidator(config={})

constraints = [
    Constraint(
        type=ConstraintType.TEMPORAL,
        parameters={"max_makespan": 120.0},
        severity=Severity.HARD,
    ),
    Constraint(
        type=ConstraintType.SPATIAL,
        parameters={"min_separation": 0.3},
        severity=Severity.HARD,
    ),
]

result = validator.validate(execution_result, constraints)

print(result.is_valid)            # True/False
print(result.violations)          # 违反的约束列表
print(result.metrics)             # 计算的指标
print(result.summary)             # 文字摘要
```

#### 验证维度

| 维度 | 检查内容 |
|------|---------|
| 任务完成度 | 所有任务是否成功完成 |
| 时间约束 | makespan < max_makespan |
| 资源约束 | 无超负载、无碰撞 |
| 空间约束 | 机械臂间距 > min_separation |

### ExceptionHandler

检测异常并确定恢复策略。

```python
from harness.exception_handler import ExceptionHandler, ExceptionType

handler = ExceptionHandler(config={})

try:
    # 执行任务...
    pass
except Exception as e:
    recovery = handler.handle(e, context={
        "task_id": "t_001",
        "arm_id": "arm_001",
        "attempt": 1,
    })

    print(recovery.action_type)  # "retry" / "skip" / "fallback" / "replan"
    print(recovery.parameters)   # 恢复参数
    print(recovery.priority)     # 优先级
```

#### 异常分类与恢复

```python
class ExceptionType(Enum):
    TIMEOUT = "timeout"                      # → retry
    RESOURCE_CONFLICT = "resource_conflict"  # → replan
    COLLISION = "collision"                  # → retry (调整路径)
    SIMULATION_ERROR = "simulation_error"    # → fallback
    CODE_GENERATION_ERROR = "code_error"     # → retry + 模板回退
    CONSTRAINT_VIOLATION = "constraint"      # → skip 或 replan
```

#### 统计追踪

```python
# 查看异常统计
stats = handler.get_statistics()
# {
#     "total_exceptions": 15,
#     "by_type": {"timeout": 8, "collision": 4, ...},
#     "recovery_success_rate": {"retry": 0.75, "fallback": 1.0, ...},
# }
```

### FeedbackLoop

闭环反馈机制，采集执行数据 → 分析瓶颈 → 调整策略。

```python
from harness.feedback_loop import FeedbackLoop

loop = FeedbackLoop(config={})

# 1. 采集反馈
loop.collect_feedback({
    "task_id": "t_001",
    "arm_id": "arm_001",
    "status": "failure",
    "duration": 5.2,
    "resource_usage": {"arm_001": 5.2},
    "errors": ["Timeout"],
})

# 2. 分析
analysis = loop.analyze_feedback()
print(analysis.performance_score)   # 0.6
print(analysis.bottlenecks)         # ["Arm arm_001 has low success rate (67%)"]
print(analysis.recommendations)     # ["Consider increasing retry_count"]

# 3. 调整策略
adjustments = loop.adjust_strategy(analysis)
for adj in adjustments:
    print(adj.target_module)    # "resource_allocator" / "code_generator"
    print(adj.parameter)        # "speed_factor" / "force_factor"
    print(adj.old_value)        # 1.0
    print(adj.new_value)        # 0.8
    print(adj.reason)           # "High failure rate; slowing movements"
```

#### 可调参数（6个）

| 参数 | 目标模块 | 范围 | 默认值 | 触发条件 |
|------|---------|------|:------:|----------|
| `timeout_adjustment` | ResourceAllocator | [0.5, 5.0] | 1.0 | 性能评分 < 0.8 |
| `retry_count` | ExceptionHandler | [1, 10] | 3 | 成功率低 |
| `resource_weight` | ResourceAllocator | [0.0, 1.0] | 0.5 | 机械臂过载 |
| `priority_boost` | ResourceAllocator | [0.0, 2.0] | 0.0 | 频繁失败 |
| `speed_factor` | CodeGenerator | [0.1, 3.0] | 1.0 | 失败率 > 20% |
| `force_factor` | CodeGenerator | [0.5, 3.0] | 1.0 | 失败率 > 20% |

## 闭环数据流

```
执行失败/超时
    │
    ▼
ExceptionHandler.handle()
    │
    ├── retry ──▶ CodeGenerator(feedback=error) ──▶ 重新执行
    ├── replan ──▶ TaskPlanner(adjusted_params) ──▶ 重新分配
    ├── fallback ──▶ 模板代码 ──▶ 重新执行
    └── skip ──▶ 标记失败 ──▶ 继续下一任务
         │
         ▼
FeedbackLoop.collect() ──▶ analyze() ──▶ adjust()
         │
         ▼
更新策略参数（超时、重试次数、权重等）
         │
         ▼
下一次调度使用新参数
```
