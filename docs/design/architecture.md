# 系统架构设计文档

## 1. 系统概述

多机械臂调度智能体（Multi-Arm Scheduling Agent）是一个基于LLM的工业自动化调度系统，采用Harness Engineering约束框架，能够从自然语言指令中自动完成任务分解、资源分配、代码生成和仿真验证。

## 2. 系统分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户接口层                              │
│  自然语言指令输入 / 场景配置 / 评估报告输出                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      智能体核心层                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ TaskPlanner  │  │CodeGenerator │  │SchedulingAgent│       │
│  │  任务规划     │  │  代码生成     │  │  调度编排     │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                │                  │                │
│  ┌──────▼────────────────▼──────────────────▼───────┐       │
│  │              LLM 客户端层                         │       │
│  │  OpenAI / Anthropic / Local (可扩展)              │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Harness 约束框架层                         │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │TaskDecom- │ │ResourceAl-│ │ResultVal- │ │ExceptionH-│   │
│  │poser      │ │locator    │ │idator     │ │andler     │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
│  ┌───────────────────────────────────────────────────┐      │
│  │              FeedbackLoop (闭环反馈)               │      │
│  └───────────────────────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      仿真执行层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  MockSimulator│  │ IsaacSim     │  │  SceneBuilder│      │
│  │  (软件仿真)   │  │ (NVIDIA仿真)  │  │  (场景构建)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      评估分析层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │MetricsCalc-  │  │BenchmarkRunner│  │ Visualizer   │      │
│  │ulator        │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心模块说明

### 3.1 智能体核心层

#### SchedulingAgent (`src/agent/core.py`)
- **角色**：系统总控，编排完整调度流程
- **流程**：任务分解 → 资源分配 → 代码生成 → 执行 → 反馈
- **关键方法**：
  - `execute_scheduling()`: 执行完整调度流水线
  - `decompose_task()`: 调用TaskPlanner分解任务
  - `allocate_resources()`: 调用ResourceAllocator分配资源
  - `generate_code()`: 调用CodeGenerator生成执行代码

#### TaskPlanner (`src/agent/planner.py`)
- **角色**：将自然语言指令分解为结构化任务计划
- **方法**：
  - LLM模式：使用结构化提示词让LLM输出JSON任务计划
  - 启发式模式：基于关键词匹配和场景配置生成任务
- **输出**：`TaskPlan` 包含任务列表、依赖图、预估makespan

#### CodeGenerator (`src/agent/code_generator.py`)
- **角色**：为每个任务生成可执行的Python代码
- **方法**：
  - 模板模式：基于操作类型组合原子原语（move_to, grip, release, ...）
  - LLM模式：使用提示词让LLM生成代码
  - 精炼模式：基于执行反馈优化代码
- **原子原语**：move_to, grip, release, rotate, linear_move, wait, check_sensor, set_payload, set_compliance

### 3.2 LLM客户端层 (`src/agent/llm_clients/`)

- `LLMClient` (ABC): 统一接口，支持 generate() 和 generate_structured()
- `OpenAIClient`: OpenAI API实现，支持JSON mode
- `AnthropicClient`: Anthropic API实现
- `create_llm_client()`: 工厂函数，根据配置创建客户端

### 3.3 Harness约束框架层 (`src/harness/`)

详见 [Harness框架设计文档](harness_design.md)

### 3.4 仿真执行层 (`src/simulation/`)

- `SimulationInterface` (ABC): 统一仿真接口
- `MockSimulator`: 软件仿真，用于无GPU环境测试
- `IsaacSimInterface`: NVIDIA Isaac Sim封装（优雅降级）
- `SceneBuilder`: 场景构建器，支持从配置文件或参数构建产线场景

### 3.5 评估分析层 (`src/evaluation/`)

- `MetricsCalculator`: 计算makespan、成功率、资源利用率、约束违反
- `BenchmarkRunner`: 加载基准数据集，运行对比实验
- `Visualizer`: 生成甘特图、资源利用率图、对比图、HTML报告

## 4. 数据流

### 4.1 调度执行流

```
用户输入 (NL指令 + 场景配置)
    │
    ▼
TaskPlanner.create_plan()
    │  输出: TaskPlan (tasks + dependency_graph)
    ▼
ResourceAllocator.allocate()
    │  输出: Dict[task_id → arm_id]
    ▼
CodeGenerator.generate() × N
    │  输出: 每个任务的可执行Python代码
    ▼
SimulationInterface.execute_action() × N
    │  输出: ActionResult (success, duration, position)
    ▼
FeedbackLoop.collect_feedback() → analyze → adjust
    │  输出: StrategyAdjustment
    ▼
ResultValidator.validate()
    │  输出: ValidationResult
    ▼
ExecutionResult (综合报告)
```

### 4.2 反馈闭环流

```
执行失败/超时
    │
    ▼
ExceptionHandler.handle()
    │  输出: RecoveryAction (retry/skip/fallback/replan)
    │
    ├── retry ──▶ CodeGenerator.generate(feedback=...) ──▶ 重新执行
    ├── replan ──▶ TaskPlanner.create_plan(调整后) ──▶ 重新分配
    ├── fallback ──▶ 使用模板代码 ──▶ 重新执行
    └── skip ──▶ 标记失败，继续下一任务
```

## 5. 关键设计决策

### 5.1 动态代码生成 vs 固定技能库

**设计选择**：动态代码生成

**原因**：
- 固定技能库无法覆盖所有工业场景
- 动态生成允许根据具体任务需求组合原子原语
- LLM可以根据上下文生成更优化的代码
- 反馈机制可以持续改进代码质量

### 5.2 启发式回退

**设计选择**：LLM优先，启发式回退

**原因**：
- LLM提供更智能的决策，但可能失败或延迟
- 启发式方法保证系统在任何情况下都能运行
- 平滑降级策略确保系统鲁棒性

### 5.3 Mock仿真

**设计选择**：提供Mock仿真器

**原因**：
- Isaac Sim需要NVIDIA GPU和特定环境
- Mock仿真允许在任何环境开发和测试
- 加速开发迭代周期
- 支持CI/CD流水线

## 6. 技术栈

| 层次 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| LLM | OpenAI GPT-4, Anthropic Claude |
| 仿真 | NVIDIA Isaac Sim, Mock Simulator |
| 优化 | OR-Tools, PuLP |
| 可视化 | Matplotlib, Plotly |
| 配置 | YAML |
| 测试 | Pytest |

## 7. 扩展点

1. **新LLM提供商**：实现 `LLMClient` 接口
2. **新仿真后端**：实现 `SimulationInterface` 接口
3. **新评估指标**：扩展 `MetricsCalculator`
4. **新恢复策略**：扩展 `ExceptionHandler`
5. **新操作类型**：在 `CodeGenerator` 中添加新的组合模式
