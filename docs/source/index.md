# Multi-Arm Scheduling Agent

<div align="center">

**基于 LLM 与 Harness Engineering 的多机械臂调度智能体**

</div>

---

Multi-Arm Scheduling Agent 是一个由大语言模型驱动的工业多机械臂调度系统。它能从自然语言指令中理解任务需求，自动完成 **任务分解 → 资源分配 → 代码生成 → 仿真验证** 的完整闭环，并通过 Harness Engineering 约束框架保证调度的可靠性和可追溯性。

## 核心特性

| 特性 | 描述 |
|------|------|
| 🧠 **LLM 驱动调度** | DeepSeek-V4-Flash 分解指令为任务 DAG；LLM 不可用时回退到启发式 |
| 🎯 **动态代码生成** | 基于 9 种原子原语按需组合生成执行代码，不依赖预置固定技能库 |
| 🔄 **闭环反馈** | 仿真结果实时回传 Harness，动态调整超时、重试、资源权重等参数 |
| 🔌 **多仿真后端** | Mock / Isaac Sim / Omniverse / Isaac Lab 四种后端无缝切换 |
| 📊 **严格评估** | makespan / 成功率 / 利用率 / 违反次数 + 配对 t 检验 |

## 快速预览

```python
import yaml
from agent.core import SchedulingAgent

# 加载配置和场景
config = yaml.safe_load(open("configs/agent_config.yaml"))
scene = yaml.safe_load(open("data/scenarios/assembly_line_4station.yaml"))["scenario"]

# 创建智能体并执行
agent = SchedulingAgent(config)
result = agent.execute_scheduling(
    instruction=scene["instruction"],
    scene_config=scene,
)

print(f"Makespan: {result.makespan:.1f}s")           # 总完工时间
print(f"Success: {result.task_success_rate:.0%}")     # 任务成功率
print(f"Violations: {result.constraint_violations}")  # 约束违反次数
```

## 文档导航

| 章节 | 内容 |
|------|------|
| [Quickstart](quickstart.md) | 5 分钟安装运行 |
| [Concepts](concepts.md) | 核心概念：任务、臂、原语、Harness |
| [Task Decomposition](tasks.md) | 从自然语言到结构化任务 |
| [Scheduling](scheduling.md) | 资源分配与调度策略 |
| [Code Generation](code_generation.md) | 原子原语与动态代码生成 |
| [Simulation](simulation.md) | Mock / Isaac Sim / Omniverse / Isaac Lab |
| [Evaluation](evaluation.md) | 指标计算与基准对比 |
| [Harness Framework](harness.md) | 闭环反馈与异常处理 |
| [Configuration](configuration.md) | 配置文件说明 |
| [API Reference](api_reference.md) | 类与函数接口 |

## 引用

本系统使用 [MRTA-Benchmark (APEX-MR)](https://github.com/intelligent-control-lab/APEX-MR) 作为评估基准数据集。
