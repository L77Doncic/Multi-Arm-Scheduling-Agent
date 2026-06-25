# 🤖 Multi-Arm Scheduling Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-DeepSeek%20Chat-purple?logo=huggingface&logoColor=white)](https://platform.deepseek.com/)
[![Simulator](https://img.shields.io/badge/simulation-PhysXOnly%20Simulator-orange)](docs/design/architecture.md)
[![Framework](https://img.shields.io/badge/framework-Harness%20Engineering-teal)](docs/design/harness_design.md)

**基于 LLM（DeepSeek Chat）与 Harness Engineering 的多机械臂调度智能体代码生成与仿真验证系统**

*An LLM-driven multi-arm scheduling agent with harness engineering constraints for industrial automation (DeepSeek Chat + PhysXOnlySimulator)*

[English](#-overview) | [中文](#-项目概述) | [文档](docs/design/architecture.md) | [快速开始](#-quick-start) | [API](docs/design/api_reference.md)

</div>

---

## 🌟 Overview

Multi-Arm Scheduling Agent is an LLM-driven industrial multi-arm robotic scheduling system. Given a natural language instruction and a production line scenario, it automatically performs:

```
Natural Language → Task Decomposition → Resource Allocation → Code Generation → Simulation → Feedback → Metrics
```

### Key Features

| Feature | Description |
|---------|-------------|
| 🧠 **LLM-Powered Scheduling** | DeepSeek Chat decomposes instructions into structured task DAGs; falls back to heuristics if LLM is unavailable |
| 🔄 **Dynamic Resource Allocation** | Greedy capability matching + 4 conflict types + load balancing + parallel opportunity scoring |
| ✅ **Closed-Loop Feedback** | Simulation results flow back to adjust 6 strategy parameters (timeout, retry, resource_weight, priority_boost, speed_factor, force_factor) |
| 🎯 **Dynamic Code Generation** | Composes executable code from 9 atomic primitives — no fixed skill library |
| 🔌 **PhysX Physics Simulation** | Pure physics computation + MRTA travel time matrix — scheduling metrics unaffected by rendering backend |
| 📊 **MRTA-Benchmark** | 6 production line scenarios with travel time matrices, MILP optimal baseline |

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

python -m venv venv
source venv/bin/activate  # Linux/Mac | venv\Scripts\activate on Windows

pip install -r requirements.txt
pip install -e .
```

### Run Your First Simulation

```bash
# Run simulation (PhysXOnlySimulator, no GPU required)
python scripts/run_simulation.py --scenario data/scenarios/1p_production_line.json

# Run single experiment with seed
python scripts/_run_single.py data/scenarios/1p_production_line.json 42 outputs/experiments
```

<details>
<summary>📖 Expected Output</summary>

```
======================================================================
SIMULATION RESULTS
======================================================================
Execution ID:    a1b2c3d4
Scenario:        MRTA-1p-ProductionLine
Tasks:           8
Makespan:        704.6s
Optimal:         584.9s (MRTA baseline)
Ratio:           1.20x
Success Rate:    80.0%
Resource Util:   44.0%
Violations:      0
```
</details>

### Python API

```python
import json, yaml
from agent.core import SchedulingAgent

# Load config and scenario
config = yaml.safe_load(open("configs/agent_config.yaml"))
scene = json.load(open("data/scenarios/1p_production_line.json"))["scenario"]

# Create agent and execute
agent = SchedulingAgent(config)
result = agent.execute_scheduling(
    instruction=scene["instruction"],
    scene_config=scene,
)

print(f"Makespan: {result.makespan:.1f}s | Success: {result.task_success_rate:.0%}")
```

> [!TIP]
> No GPU or LLM API key? The system automatically falls back to heuristic task decomposition and template-based code generation. All features remain functional.

---

## ⚙️ Configuration

### LLM Setup

Configure in `configs/agent_config.yaml`:

```yaml
llm:
  provider: "openai"                          # OpenAI-compatible API
  model: "deepseek-chat"                      # DeepSeek Chat model
  api_base: "https://api.deepseek.com/v1"
  api_key_env: "OPENAI_API_KEY"               # Read key from env var
  temperature: 0.7
  top_p: 0.9
  max_tokens: 4096
```

Set your API key via environment variable or `.env` file:

```bash
# Option 1: Environment variable
export OPENAI_API_KEY="your-api-key-here"

# Option 2: .env file
echo 'OPENAI_API_KEY=your-api-key-here' > .env
```

> **Note**: 原使用的 mimo-v2.5 模型因长 prompt 超时问题，已切换为 DeepSeek Chat。两者均为 OpenAI 兼容 API，切换无需修改代码。

<details>
<summary>🔧 Supported LLM Providers</summary>

| Provider | `llm.provider` | Model Example | API Base |
|----------|----------------|---------------|----------|
| DeepSeek | `"openai"` | `deepseek-chat` | `https://api.deepseek.com/v1` |
| OpenAI | `"openai"` | `gpt-4-turbo` | `https://api.openai.com/v1` |
| Anthropic | `"anthropic"` | `claude-3-opus-20240229` | `https://api.anthropic.com` |
| Local | — | — | Heuristic fallback (no API needed) |
</details>

### Simulation Backend

```bash
# PhysXOnlySimulator (default, no GPU required)
python scripts/run_simulation.py --scenario data/scenarios/1p_production_line.json

# Run all experiments (6 scenarios × 5 seeds = 30 runs)
python scripts/run_all_experiments.py
```

| Backend | GPU Required | Physics | Use Case |
|---------|:------------:|---------|----------|
| `physx_only` | No | 纯物理计算 + MRTA 旅行时间矩阵 | 调度指标评估（当前默认） |
| `isaac` | Yes (RTX) | PhysX + USD 渲染 | 物理仿真验证（需 Vulkan 驱动） |

> **Note**: 当前容器环境 Vulkan 驱动不可用，已切换为 PhysXOnlySimulator。该后端通过纯物理计算 + MRTA 旅行时间矩阵（T_t）计算 Makespan，与 MILP 基准完全可比，不影响调度指标的准确性。视频录制功能已移除。

---

## 📊 Evaluation

### Run Benchmark

```bash
# Run all experiments (6 scenarios × 5 seeds = 30 runs)
python scripts/run_all_experiments.py

# Run single experiment
python scripts/_run_single.py data/scenarios/1p_production_line.json 42 outputs/experiments
```

### Metrics

| Metric | Formula | Direction |
|--------|---------|-----------|
| **Makespan** | `max(end_time) - min(start_time)` | ↓ Minimize |
| **Task Success Rate** | `completed_tasks / total_tasks` | ↑ Maximize |
| **Resource Utilization** | `sum(durations) / (makespan × num_arms)` | ↑ Maximize |
| **Constraint Violations** | Count of overlaps + capability mismatches | ↓ Minimize |

### MRTA-Benchmark Results (30 次实验, DeepSeek Chat + PhysXOnlySimulator)

| 场景 | 任务数 | Makespan | 最优 Makespan | 比率 | 成功率 | 利用率 |
|------|:------:|:--------:|:-------------:|:----:|:------:|:------:|
| 1p | 8 | 704.6s | 584.9s | 1.20x | 80% | 44% |
| 2p | 8 | 684.9s | 931.0s | 0.74x | 80% | 47% |
| 3p | 8 | 854.1s | 642.8s | 1.33x | 72% | 47% |
| 4p | 8 | 739.5s | 465.0s | 1.59x | 82% | 40% |
| 5p | 8 | 654.0s | 490.9s | 1.33x | 80% | 50% |
| 6p | 8 | 460.1s | 489.8s | 0.94x | 88% | 57% |
| **平均** | — | **682.9s** | — | **1.19x** | **80%** | **47%** |

> 每个场景运行 5 次（不同 seed），共 30 次实验。Makespan 比率 = 系统 Makespan / MILP 最优 Makespan，越接近 1.0 越优。

See [`docs/reports/evaluation_report.md`](docs/reports/evaluation_report.md) for full details.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    User Input                                 │
│         Natural Language + Scene Config (YAML)                │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 SchedulingAgent (core.py)                     │
│                                                               │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────┐  │
│  │ TaskPlanner   │  │ CodeGenerator  │  │ ResourceAllocator │  │
│  │ (LLM/Heurist.)│  │ (LLM/Template) │  │ (Greedy+Conflict) │  │
│  └──────┬───────┘  └───────┬───────┘  └─────────┬─────────┘  │
│         └──────────┬───────┘                     │            │
│                    ▼                             ▼            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Simulation Execution                          │  │
│  │   ArmInterface → PhysXOnlySimulator / Isaac Sim        │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                   │
│      ┌────────────────────┼────────────────────┐              │
│      ▼                    ▼                    ▼              │
│ ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     │
│ │Feedback  │    │ResultValidator│    │ExceptionHandler  │     │
│ │  Loop    │    │               │    │                  │     │
│ └────┬─────┘    └───────────────┘    └──────────────────┘     │
│      │                                                        │
│      ▼                                                        │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │              MetricsCalculator                            │ │
│ │  makespan │ success_rate │ utilization │ violations      │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Harness Engineering Framework

Five interconnected modules ensure reliable, traceable scheduling:

| Module | File | Responsibility |
|--------|------|----------------|
| **TaskDecomposer** | `harness/task_decomposer.py` | NL instruction → structured subtasks + dependency DAG |
| **ResourceAllocator** | `harness/resource_allocator.py` | Greedy matching + 4 conflict types + load balancing + parallel opportunity scoring |
| **ResultValidator** | `harness/result_validator.py` | Temporal / spatial / resource constraint checking |
| **ExceptionHandler** | `harness/exception_handler.py` | 7 exception types + 4 recovery strategies + escalation |
| **FeedbackLoop** | `harness/feedback_loop.py` | Performance analysis → strategy parameter adjustment |

### Closed-Loop Feedback

When simulation detects failures or bottlenecks:

```
Simulation → collect_feedback() → analyze_feedback() → adjust_strategy()
                                                         │
                    ┌────────────────────────────────────┘
                    ▼
            ┌───────────────────┐
            │ Strategy Adjustment│
            │ • timeout ↑        │
            │ • retry_count ↑    │
            │ • resource_weight ↑│
            │ • priority_boost ↑ │
            └───────────────────┘
```

> [!IMPORTANT]
> The feedback loop is **not optional**. Every task execution feeds back into the strategy, enabling adaptive scheduling. See [Harness Design](docs/design/harness_design.md) for details.

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/design/architecture.md) | System architecture, module responsibilities, data flow |
| [Harness Design](docs/design/harness_design.md) | Five-module framework design with interaction diagrams |
| [API Reference](docs/design/api_reference.md) | Complete API documentation for 11 core classes |
| [Benchmark Spec](data/benchmark_specification.md) | Unified benchmark sources and evaluation protocol |
| [Quickstart](docs/source/quickstart.md) | 5-minute installation and first run |
| [Concepts](docs/source/concepts.md) | Core concepts: Tasks, Arms, Primitives, Harness |

---

## 📁 Project Structure

```
Multi-Arm-Scheduling-Agent/
├── src/
│   ├── agent/                         # LLM agent core
│   │   ├── core.py                    # Main scheduler (6-step pipeline)
│   │   ├── planner.py                 # Task planner (LLM/heuristic)
│   │   ├── code_generator.py          # Code generator (LLM/template)
│   │   ├── llm_clients/
│   │   │   ├── sync_client.py         # Sync LLM client (OpenAI-compatible)
│   │   │   ├── openai_client.py       # OpenAI client
│   │   │   └── anthropic_client.py    # Anthropic client
│   │   └── prompts/                   # Prompt templates
│   ├── harness/                       # Harness Engineering framework
│   │   ├── task_decomposer.py         # Task decomposition
│   │   ├── resource_allocator.py      # Resource allocation
│   │   ├── result_validator.py        # Result validation
│   │   ├── exception_handler.py       # Exception handling
│   │   └── feedback_loop.py           # Closed-loop feedback
│   ├── simulation/                    # Simulation interfaces
│   │   ├── base.py                    # Abstract interface (SimulationInterface)
│   │   ├── isaac_sim.py               # Isaac Sim 4.5 backend
│   │   ├── physx_only.py              # PhysXOnlySimulator (当前默认)
│   │   ├── mrta_travel.py             # MRTA travel time manager
│   │   └── arm_interface.py           # Primitive → simulation adapter
│   └── evaluation/                    # Evaluation module
│       ├── metrics.py                 # Metric calculation
│       ├── benchmark.py               # Benchmark + t-test
│       ├── mrta_loader.py             # APEX-MR dataset loader
│       └── visualizer.py              # Gantt charts + HTML reports
├── configs/                           # Configuration files
├── data/
│   ├── datasets/MRTA-Benchmark/       # APEX-MR dataset
│   ├── scenarios/                     # 6 production line scenarios (JSON)
│   │   ├── 1p_production_line.json    # 1 workpiece, 4 stations, 3 arms
│   │   ├── 2p_production_line.json    # 2 workpieces
│   │   ├── 3p_production_line.json    # 3 workpieces
│   │   ├── 4p_production_line.json    # 4 workpieces
│   │   ├── 5p_production_line.json    # 5 workpieces
│   │   └── 6p_production_line.json    # 6 workpieces
│   └── benchmark_specification.md     # Unified benchmark spec
├── docs/
│   ├── design/                        # Design documents
│   │   ├── architecture.md
│   │   ├── harness_design.md
│   │   └── api_reference.md
│   └── source/                        # User documentation
├── scripts/
│   ├── run_simulation.py              # Simulation runner
│   ├── run_all_experiments.py         # Batch experiment runner (6×5=30)
│   ├── _run_single.py                 # Single experiment runner
│   ├── evaluate.py                    # Evaluation script
│   └── evaluate_rigorous.py           # Rigorous evaluation (NeurIPS)
├── outputs/experiments/               # 30 experiment result JSONs
├── tests/                             # Unit + integration tests
├── requirements.txt
└── setup.py
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 🙏 Acknowledgements

- [APEX-MR](https://github.com/intelligent-control-lab/APEX-MR) — MRTA-Benchmark dataset (RSS 2025)
- [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim) — Physics simulation platform
- [DeepSeek](https://platform.deepseek.com/) — LLM inference API (DeepSeek Chat)
- [OpenHarness](https://github.com/HKUDS/OpenHarness) — Harness Engineering architecture reference

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📫 Citation

If you use this system in your research, please cite:

```bibtex
@software{multi_arm_scheduling_agent,
  title  = {Multi-Arm Scheduling Agent: LLM-Driven Industrial Robotics Scheduling},
  author = {L77Doncic},
  url    = {https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent},
  year   = {2026}
}
```

---

<div align="center">

**⭐ If this project helps you, please give it a star! ⭐**

</div>
