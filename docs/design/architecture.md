# 系统架构设计

## 1. 系统概述

Multi-Arm Scheduling Agent 是一个基于大语言模型（LLM）的多机械臂调度智能体系统，
在 Harness Engineering 约束框架下运行。系统从自然语言指令和产线场景配置出发，
自动完成工序分解、机械臂分配、执行顺序调度，并接入仿真环境完成执行验证。

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户输入                                  │
│            自然语言指令 + 产线场景配置 (JSON)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SchedulingAgent (core.py)                     │
│                                                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐    │
│  │  TaskPlanner  │  │ CodeGenerator  │  │ ResourceAllocator  │    │
│  │  (LLM/启发式) │  │ (LLM/模板)    │  │ (贪心+冲突检测)     │    │
│  └──────┬───────┘  └───────┬───────┘  └─────────┬──────────┘    │
│         │                  │                     │               │
│         ▼                  ▼                     ▼               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Simulation Execution                          │  │
│  │  ArmInterface → IsaacSim (PhysX物理仿真)                   │  │
│  └──────────────────────────────┬────────────────────────────┘  │
│                                 │                                │
│         ┌───────────────────────┼───────────────────┐            │
│         ▼                       ▼                   ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │ FeedbackLoop  │    │ResultValidator│    │ ExceptionHandler  │  │
│  │ (闭环反馈)    │    │ (结果验证)    │    │ (异常处理)        │  │
│  └──────┬───────┘    └──────────────┘    └────────────────────┘  │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                MetricsCalculator                          │   │
│  │  makespan / success_rate / utilization / violations       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ExecutionResult                            │
│  execution_id, tasks, allocation, makespan,                      │
│  task_success_rate, resource_utilization,                        │
│  constraint_violations, execution_log,                           │
│  feedback_adjustments, generated_codes                           │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 核心模块

### 3.1 Agent 模块 (`src/agent/`)

LLM 驱动的智能体核心，负责任务理解和代码生成。

| 组件 | 文件 | 职责 |
|------|------|------|
| `SchedulingAgent` | `core.py` | 主调度器，编排完整 6 步管线 |
| `TaskPlanner` | `planner.py` | LLM/启发式任务分解，生成依赖图 |
| `CodeGenerator` | `code_generator.py` | LLM/模板代码生成，基于 9 个原子原语 |
| `SyncLLMClient` | `llm_clients/sync_client.py` | 同步 LLM 客户端（OpenAI 兼容 API） |
| `Prompts` | `prompts/*.py` | 任务分解、资源分配、代码生成的提示词模板 |

### 3.2 Harness 模块 (`src/harness/`)

约束框架，确保调度可靠性和可追溯性。

| 组件 | 文件 | 职责 |
|------|------|------|
| `TaskDecomposer` | `task_decomposer.py` | 自然语言 → 结构化子任务 |
| `ResourceAllocator` | `resource_allocator.py` | 贪心分配 + 冲突检测 + 负载均衡 |
| `ResultValidator` | `result_validator.py` | 时间/空间/资源约束验证 |
| `ExceptionHandler` | `exception_handler.py` | 异常分类 + 恢复策略 + 统计 |
| `FeedbackLoop` | `feedback_loop.py` | 闭环反馈 + 性能分析 + 策略调整 |

### 3.3 Simulation 模块 (`src/simulation/`)

统一仿真接口，支持三种后端，当前主要使用 Isaac Sim。

| 组件 | 文件 | 职责 |
|------|------|------|
| `SimulationInterface` | `base.py` | 抽象仿真接口 |
| `IsaacSimInterface` | `isaac_sim.py` | Isaac Sim 4.5 物理仿真（默认） |
| `OmniverseInterface` | `omniverse.py` | Omniverse Kit 后端 |
| `IsaacLabInterface` | `isaac_lab.py` | Isaac Lab 后端 |
| `ArmInterface` | `arm_interface.py` | 原子原语 → 仿真动作适配器 |

### 3.4 Evaluation 模块 (`src/evaluation/`)

评估指标计算和基准对比。

| 组件 | 文件 | 职责 |
|------|------|------|
| `MetricsCalculator` | `metrics.py` | makespan/成功率/利用率/违反次数 |
| `BenchmarkRunner` | `benchmark.py` | 基准测试 + 配对 t 检验 |
| `MRTABenchmarkLoader` | `mrta_loader.py` | APEX-MR 数据集加载 + 场景转换 |
| `Visualizer` | `visualizer.py` | 甘特图 / 利用率图 / HTML 报告 |

## 4. 数据流

完整的 6 步调度管线：

```
Step 1: 任务分解 (TaskPlanner)
   instruction + scene_config → TaskPlan
   TaskPlan = {tasks: [TaskNode], dependency_graph, estimated_makespan}

Step 2: 资源分配 (ResourceAllocator)
   tasks + robot_arms → allocation {task_id: arm_id}
   评分: 0.6×capability + 0.3×workload_balance + 0.1×priority

Step 3: 代码生成 (CodeGenerator)
   task + arm + parameters → GeneratedCode
   GeneratedCode.code = "def execute_task(arm_interface): ..."
   基于 9 个原子原语动态编排

Step 4: 仿真执行 (ArmInterface + Simulator)
   generated_code + simulation → execution_log
   每个 execute_*() 函数通过 ArmInterface 调用原子原语
   原语调用被翻译为仿真动作并执行

Step 5: 闭环反馈 (FeedbackLoop)
   execution_log → collect_feedback → analyze_feedback → adjust_strategy
   策略调整: timeout↑, retry↑, resource_weight↑, priority_boost↑

Step 6: 指标计算 (MetricsCalculator)
   execution_log → makespan, success_rate, utilization, violations
```

## 5. LLM 集成

### 配置

```yaml
llm:
  provider: "openai"                          # OpenAI 兼容 API
  model: "mimo-v2.5"                          # Xiaomi MiMo 模型
  api_base: "https://token-plan-cn.xiaomimimo.com/v1"
  api_key: "your-api-key"
  temperature: 0.7
  top_p: 0.9
  max_tokens: 4096
```

### 使用场景

| 场景 | LLM 用途 | 回退方案 |
|------|----------|----------|
| `TaskPlanner._plan_with_llm()` | 分解自然语言指令为结构化任务 | `_plan_with_heuristics()` |
| `CodeGenerator._generate_with_llm()` | 生成基于原子原语的可执行代码 | `_generate_with_template()` |
| `CodeGenerator._refine_with_llm()` | 基于执行反馈精炼代码 | `_generate_with_template()` |

### SyncLLMClient 接口

```python
client = SyncLLMClient(config)

# 文本生成
text = client.generate("Decompose this instruction: ...")

# 结构化 JSON 生成
result = client.generate_structured(
    "Return tasks as JSON",
    schema={"type": "object", "properties": {...}}
)
```

## 6. 仿真后端

当前主要使用 Isaac Sim 4.5 作为仿真后端：

| 后端 | GPU 需求 | 物理引擎 | 使用场景 |
|------|:--------:|----------|----------|
| `isaac` | ✅ RTX GPU | PhysX | 物理级验证（碰撞、力学） |

### 使用 Isaac Sim

```python
from simulation.isaac_sim import IsaacSimInterface

sim = IsaacSimInterface(fallback_to_mock=False)
sim.initialize()
sim.load_scene(scene_config)
```

## 7. 关键设计决策

### 为什么用动态代码生成而非固定技能库？

| 方案 | 优点 | 缺点 |
|------|------|------|
| 固定技能库 | 简单、确定性高 | 无法覆盖所有场景，灵活性差 |
| **动态代码生成** | 灵活、可适配任意任务 | 代码质量依赖 LLM/模板 |

系统选择动态代码生成，因为工业场景千变万化，固定技能库无法满足所有需求。
LLM 根据具体任务参数（目标位置、力控参数、传感器类型）实时组合原子原语。

### 为什么用 6 步管线而非端到端？

- **可解释性**: 每步输出可审计（任务图、分配方案、生成代码、执行日志）
- **可干预性**: 任何一步可被替换或跳过
- **可测试性**: 每步有明确的输入输出接口
- **容错性**: 单步失败不影响其他步骤
