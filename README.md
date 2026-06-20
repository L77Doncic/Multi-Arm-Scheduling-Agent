# 🤖 Multi-Arm Scheduling Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-DeepSeek--V4-purple?logo=huggingface&logoColor=white)](https://www.modelscope.cn/)
[![Simulator](https://img.shields.io/badge/simulation-Mock%20%7C%20Isaac%20Sim%20%7C%20Omniverse%20%7C%20Isaac%20Lab-orange)](docs/design/architecture.md)
[![Framework](https://img.shields.io/badge/framework-Harness%20Engineering-teal)](docs/design/harness_design.md)

**基于 LLM 与 Harness Engineering 的多机械臂调度智能体代码生成与仿真验证系统**

*An LLM-driven multi-arm scheduling agent with harness engineering constraints for industrial automation*

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
| 🧠 **LLM-Powered Scheduling** | DeepSeek-V4-Flash decomposes instructions into structured task DAGs; falls back to heuristics if LLM is unavailable |
| 🔄 **Dynamic Resource Allocation** | Greedy capability matching + conflict detection + load balancing across robot arms |
| ✅ **Closed-Loop Feedback** | Simulation results flow back to adjust timeout, retry count, resource weights, and task priority |
| 🎯 **Dynamic Code Generation** | Composes executable code from 9 atomic primitives — no fixed skill library |
| 🔌 **Multi-Backend Simulation** | Mock / Isaac Sim / Omniverse / Isaac Lab — unified `SimulationInterface`, zero code change to switch |
| 📊 **Rigorous Evaluation** | Makespan, success rate, utilization, constraint violations + paired t-test (NeurIPS standard) |

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
# Using Mock simulator (no GPU required)
python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml
```

<details>
<summary>📖 Expected Output</summary>

```
======================================================================
SIMULATION RESULTS
======================================================================
Execution ID:    c97c0ca2
Tasks:           14
Makespan:        23.00s
Success Rate:    100.0%
Resource Util:   66.7%
Violations:      3

TASK DETAILS:
  ✓ t_001  | Pick and load workpiece A    | arm=arm_001 | completed
  ✓ t_002  | Transport workpiece A         | arm=arm_001 | completed
  ✓ t_003  | Assemble components of A      | arm=arm_001 | completed
  ...
```
</details>

### Python API (3 Lines)

```python
import yaml
from agent.core import SchedulingAgent

# Load config and scenario
config = yaml.safe_load(open("configs/agent_config.yaml"))
scene = yaml.safe_load(open("data/scenarios/assembly_line_4station.yaml"))["scenario"]

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
  model: "deepseek-ai/DeepSeek-V4-Flash"      # ModelScope model
  api_base: "https://api-inference.modelscope.cn/v1"
  api_key_env: "OPENAI_API_KEY"               # Read key from env var
  temperature: 0.7
  max_tokens: 4096
```

Set your API key via environment variable or `.env` file:

```bash
# Option 1: Environment variable
export OPENAI_API_KEY="your-api-key-here"

# Option 2: .env file (copy .env.example)
cp .env.example .env
# Edit .env and fill in your key
```

<details>
<summary>🔧 Supported LLM Providers</summary>

| Provider | `llm.provider` | Model Example | API Base |
|----------|----------------|---------------|----------|
| ModelScope | `"openai"` | `deepseek-ai/DeepSeek-V4-Flash` | `https://api-inference.modelscope.cn/v1` |
| OpenAI | `"openai"` | `gpt-4-turbo` | `https://api.openai.com/v1` |
| Anthropic | `"anthropic"` | `claude-3-opus-20240229` | `https://api.anthropic.com` |
| Local | — | — | Heuristic fallback (no API needed) |
</details>

### Simulation Backend

```bash
# Mock (default, no GPU)
python scripts/run_simulation.py --scenario ... --sim mock

# Isaac Sim (requires NVIDIA GPU + Isaac Sim installed)
python scripts/run_simulation.py --scenario ... --sim isaac

# Omniverse
python scripts/run_simulation.py --scenario ... --sim omniverse

# Isaac Lab
python scripts/run_simulation.py --scenario ... --sim isaac_lab
```

| Backend | GPU Required | Physics | Use Case |
|---------|:------------:|---------|----------|
| `mock` | ❌ | None | Development, CI/CD, logic verification |
| `isaac` | ✅ | PhysX 5 | Physical simulation validation |
| `omniverse` | ✅ | PhysX 5 | Scene rendering + simulation |
| `isaac_lab` | ✅ | PhysX 5 | RL training + batch evaluation |

---

## 📊 Evaluation

### Run Benchmark

```bash
# Rigorous evaluation (5 runs, paired t-test, NeurIPS standard)
python scripts/evaluate_rigorous.py \
    --scenario data/scenarios/assembly_line_4station.yaml \
    --runs 5

# MRTA-Benchmark (APEX-MR) dataset evaluation
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark
```

### Metrics

| Metric | Formula | Direction |
|--------|---------|-----------|
| **Makespan** | `max(end_time) - min(start_time)` | ↓ Minimize |
| **Task Success Rate** | `completed_tasks / total_tasks` | ↑ Maximize |
| **Resource Utilization** | `sum(durations) / (makespan × num_arms)` | ↑ Maximize |
| **Constraint Violations** | Count of overlaps + capability mismatches | ↓ Minimize |

### Unified Benchmark

| Dataset | Source | Optimal Makespan | Method |
|---------|--------|:----------------:|--------|
| 4-Station Assembly Line | Custom | 25.0s | MILP |
| MRTA-Benchmark (13 tasks) | [APEX-MR](https://github.com/intelligent-control-lab/APEX-MR) (RSS 2025) | 20–95s | Paper Table 1 |

See [`data/benchmark_specification.md`](data/benchmark_specification.md) for full details.

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
│  │   ArmInterface → Mock / Isaac Sim / Omniverse / Lab    │  │
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
| **ResourceAllocator** | `harness/resource_allocator.py` | Greedy matching + 4 conflict types + load balancing |
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
│   │   │   └── sync_client.py         # Sync LLM client (ModelScope API)
│   │   └── prompts/                   # Prompt templates
│   ├── harness/                       # Harness Engineering framework
│   │   ├── task_decomposer.py         # Task decomposition
│   │   ├── resource_allocator.py      # Resource allocation
│   │   ├── result_validator.py        # Result validation
│   │   ├── exception_handler.py       # Exception handling
│   │   └── feedback_loop.py           # Closed-loop feedback
│   ├── simulation/                    # Simulation interfaces
│   │   ├── base.py                    # Abstract interface
│   │   ├── mock_simulator.py          # Pure Python simulator
│   │   ├── isaac_sim.py               # Isaac Sim backend
│   │   ├── omniverse.py               # Omniverse backend
│   │   ├── isaac_lab.py               # Isaac Lab backend
│   │   ├── scene_builder.py           # Scene builder
│   │   └── arm_interface.py           # Primitive → simulation adapter
│   └── evaluation/                    # Evaluation module
│       ├── metrics.py                 # Metric calculation
│       ├── benchmark.py               # Benchmark + t-test
│       ├── mrta_loader.py             # APEX-MR dataset loader
│       └── visualizer.py              # Gantt charts + HTML reports
├── configs/                           # Configuration files
├── data/
│   ├── datasets/MRTA-Benchmark/       # APEX-MR dataset (13 tasks)
│   ├── scenarios/                     # Scenario configs
│   └── benchmark_specification.md     # Unified benchmark spec
├── docs/
│   ├── design/                        # Design documents
│   │   ├── architecture.md
│   │   ├── harness_design.md
│   │   └── api_reference.md
│   └── source/                        # User documentation
├── scripts/
│   ├── run_simulation.py              # Simulation runner
│   ├── evaluate.py                    # Evaluation script
│   └── evaluate_rigorous.py           # Rigorous evaluation (NeurIPS)
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
- [ModelScope](https://www.modelscope.cn/) — LLM inference API
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
