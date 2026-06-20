# Harness 框架设计文档

## 1. 概述

Harness Engineering 框架是多机械臂调度智能体的约束管理核心。它提供任务分解、
资源分配、结果验证、异常处理和闭环反馈五大模块，确保 LLM 生成的调度策略
和执行代码在约束范围内运行，并通过仿真反馈持续优化。

## 2. 设计原则

1. **约束优先** — 所有调度决策必须在约束范围内
2. **闭环反馈** — 仿真结果必须回传用于策略调整
3. **优雅降级** — LLM 不可用时回退到启发式方法
4. **可观测性** — 全流程日志记录和指标追踪
5. **可扩展性** — 模块化设计，支持新增约束类型和恢复策略

## 3. 五大核心模块

### 3.1 任务分解模块 (`task_decomposer.py`)

**职责**: 将自然语言指令分解为结构化子任务

**输入**: 自然语言指令 + 场景配置
**输出**: `List[DecomposedTask]`

**流程**:

```
instruction → 模式匹配 → 操作识别 → 依赖图构建 → 任务结构化
```

**操作类型识别**:

| 操作类型 | 关键词 | 估计时长 | 所需能力 |
|----------|--------|:--------:|----------|
| `pick` | pick, grab, grasp, take, lift | 2.0s | gripper, positioning |
| `place` | place, put, position, set, drop | 2.0s | gripper, positioning |
| `move` | move, transfer, transport, carry | 3.0s | locomotion, positioning |
| `assemble` | assemble, connect, attach, join | 5.0s | gripper, force_control |
| `inspect` | inspect, check, verify, examine | 4.0s | vision, positioning |
| `tighten` | tighten, secure, bolt, screw | 3.0s | torque_control |
| `weld` | weld, solder, bond, fuse | 6.0s | welding_tool |
| `paint` | paint, coat, spray, finish | 5.0s | spray_control |

**依赖图**: 线性依赖（前序任务完成后才能执行后续任务）

### 3.2 资源分配模块 (`resource_allocator.py`)

**职责**: 将任务分配给合适的机械臂

**输入**: `List[Task]` + `List[RobotArm]`
**输出**: `Dict[task_id, arm_id]`

**算法**: 贪心 + 冲突检测 + 负载均衡

**评分公式**:

```
composite_score = capability_weight × cap_score
                + workload_weight × balance_score
                + priority_weight × priority_score
```

默认权重: `capability=0.6, workload=0.3, priority=0.1`

**冲突类型**:

| 类型 | 描述 | 解决策略 |
|------|------|----------|
| `TEMPORAL` | 同一机械臂时间重叠 | 重新分配到次优机械臂 |
| `CAPABILITY` | 机械臂缺少所需能力 | 强制重新分配 |
| `RESOURCE` | 共享资源争用 | 等待或重新分配 |
| `COLLISION` | 物理碰撞风险 | 重新规划轨迹 |

**负载均衡指标**: `1 - CV(arm_totals)`，CV 为变异系数

### 3.3 结果验证模块 (`result_validator.py`)

**职责**: 验证执行结果是否满足约束

**输入**: 执行结果 + 约束列表
**输出**: `ValidationResult {is_valid, violations, metrics, summary}`

**验证维度**:

| 维度 | 检查项 | 严重级别 |
|------|--------|----------|
| 任务完成 | 所有任务状态为 `completed` | `ERROR` |
| 时间约束 | 总时长 / 单任务时长 / 截止时间 | 可配置 |
| 资源约束 | 利用率上限 / 能耗预算 / 禁用机械臂 | 可配置 |
| 空间约束 | 工作空间边界 / 最小臂间距 / 目标位置精度 | 可配置 |

**严重级别**: `INFO < WARNING < ERROR < CRITICAL`

### 3.4 异常处理模块 (`exception_handler.py`)

**职责**: 异常分类、恢复策略选择、统计追踪

**异常类型**:

| 类型 | 默认恢复 | 最大重试 | 优先级 |
|------|----------|:--------:|:------:|
| `TIMEOUT` | RETRY | 3 | 60 |
| `RESOURCE_CONFLICT` | REPLAN | 2 | 80 |
| `COLLISION` | REPLAN | 1 | 100 |
| `COMMUNICATION_FAILURE` | RETRY | 5 | 30 |
| `SIMULATION_ERROR` | FALLBACK | 2 | 50 |
| `CODE_GENERATION_ERROR` | RETRY | 3 | 40 |
| `CONSTRAINT_VIOLATION` | REPLAN | 1 | 90 |

**恢复策略**:

| 策略 | 描述 |
|------|------|
| `RETRY` | 重试相同操作 |
| `SKIP` | 跳过失败任务 |
| `FALLBACK` | 切换到备选方案 |
| `REPLAN` | 重新规划调度 |

**升级机制**: 重试次数超限时自动升级 (`RETRY → REPLAN`)

### 3.5 闭环反馈机制 (`feedback_loop.py`)

**职责**: 收集执行反馈、分析性能、动态调整策略

**反馈流程**:

```
仿真执行 → collect_feedback → analyze_feedback → adjust_strategy → 重新调度
```

**可调策略参数**:

| 参数 | 范围 | 默认值 | 调整触发条件 |
|------|------|:------:|-------------|
| `timeout_adjustment` | [0.5, 5.0] | 1.0 | 性能评分 < 0.8 |
| `retry_count` | [1, 10] | 3 | 机械臂成功率低 |
| `resource_weight` | [0.0, 1.0] | 0.5 | 机械臂过载 |
| `priority_boost` | [0.0, 2.0] | 0.0 | 任务频繁失败 |

**性能评分**:

```
performance_score = success_rate - variance_penalty
variance_penalty = min(variance / (avg_duration + ε), 1.0) × 0.2
```

**瓶颈识别**:

- 机械臂成功率 < 70%
- 任务耗时 > 平均值 × 2
- 重复错误出现 ≥ 2 次

## 4. 模块间交互

```
                    ┌──────────────────┐
                    │  TaskDecomposer   │
                    └────────┬─────────┘
                             │ tasks
                             ▼
                    ┌──────────────────┐
                    │ ResourceAllocator │ ←──── FeedbackLoop (strategy params)
                    └────────┬─────────┘
                             │ allocation
                             ▼
                    ┌──────────────────┐
                    │   Simulation      │
                    │   Execution       │
                    └────────┬─────────┘
                             │ results
                    ┌────────┴─────────┐
                    ▼                  ▼
           ┌──────────────┐   ┌──────────────┐
           │ ResultValidator│   │ ExceptionHandler│
           └──────┬───────┘   └──────┬───────┘
                  │ violations        │ recovery
                  ▼                   ▼
           ┌──────────────────────────────┐
           │       FeedbackLoop            │
           │  collect → analyze → adjust   │
           └──────────────────────────────┘
```

## 5. 配置

Harness 框架通过 `configs/agent_config.yaml` 的 `harness` 段配置:

```yaml
harness:
  feedback:
    enabled: true
    interval: 1.0
    metrics: [task_status, resource_utilization, error_rate]

  validation:
    enabled: true
    strict_mode: false
    auto_retry: true
    max_retries: 3

  exception_handling:
    enabled: true
    log_errors: true
    notify_on_critical: true
    recovery_strategies: [retry, skip, fallback]
```

## 6. 示例：闭环反馈生效场景

当模拟器设置高失败率时，反馈循环自动触发策略调整：

```
输入: assemble 失败率 = 60%
结果: 8 任务中 2 个失败
性能评分: 0.66 (< 0.8 阈值)

自动调整:
  1. timeout_adjustment: 1.0 → 1.2
     原因: "Low performance score (0.66); increasing timeout factor"
  
  2. retry_count: 3 → 4
     原因: "Low arm success rate detected; increasing retries"

瓶颈识别:
  - Arm arm_001 has low success rate (67%)
  - Arm arm_002 has low success rate (67%)
```
