# Multi-Arm Scheduling Agent

<em>基于LLM与Harness Engineering的多机械臂调度智能体</em>

---

Multi-Arm Scheduling Agent 是一个由大语言模型驱动的工业多机械臂调度系统。它能从自然语言指令中理解任务需求，自动完成**任务分解 → 资源分配 → 代码生成 → 仿真验证**的完整闭环，并通过 Harness Engineering 约束框架保证调度的可靠性和可追溯性。

## 核心特性

<div class="grid cards" markdown>

-   :material-robot-outline:{ .lg .middle } __LLM驱动调度__

    ---

    利用大语言模型理解自然语言指令，自动分解工序、分配资源。无LLM时自动回退到启发式模式。

-   :material-code-braces:{ .lg .middle } __动态代码生成__

    ---

    基于9种原子原语（move_to, grip, release等）按需组合生成执行代码，不依赖预置固定技能库。

-   :material-sync:{ .lg .middle } __闭环反馈__

    ---

    仿真执行结果实时回传Harness，动态调整超时、重试、资源权重等策略参数。

-   :material-chart-box:{ .lg .middle } __基准评估__

    ---

    内置MRTA-Benchmark数据集，支持与Random/Greedy/Optimal基线的系统对比。

</div>

## 快速概览

```python
from agent.core import SchedulingAgent

agent = SchedulingAgent(config)
result = agent.execute_scheduling(
    instruction="Pick two workpieces, assemble them, inspect, and package",
    scene_config=scene,
    simulation=sim,
)

print(result.makespan)           # 总完工时间
print(result.task_success_rate)  # 任务成功率
print(result.constraint_violations)  # 约束违反次数
```

## 文档导航

| 章节 | 内容 |
|------|------|
| [Quickstart](quickstart.md) | 5分钟安装运行 |
| [Concepts](concepts.md) | 核心概念：任务、臂、原语、Harness |
| [Task Decomposition](tasks.md) | 从自然语言到结构化任务 |
| [Scheduling](scheduling.md) | 资源分配与调度策略 |
| [Code Generation](code_generation.md) | 原子原语与动态代码生成 |
| [Simulation](simulation.md) | Mock仿真与Isaac Sim接口 |
| [Evaluation](evaluation.md) | 指标计算与基准对比 |
| [Harness Framework](harness.md) | 闭环反馈与异常处理 |
| [Configuration](configuration.md) | 配置文件说明 |
| [API Reference](api_reference.md) | 类与函数接口 |

## 引用

本系统使用 [MRTA-Benchmark](https://github.com/intelligent-control-lab/APEX-MR) 作为评估基准数据集。
