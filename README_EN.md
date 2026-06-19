# 🤖 Multi-Arm Scheduling Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen)](#testing)

**An LLM-driven multi-arm scheduling agent with harness engineering constraints for industrial automation**

English | [中文](README.md)

</div>

---

## Overview

This project implements an LLM-driven multi-arm scheduling agent system using a Harness Engineering constraints framework. It features:

- 🧠 **Intelligent Task Decomposition**: Automatic process decomposition from natural language instructions with LLM and heuristic dual-mode support
- 🔄 **Dynamic Resource Allocation**: Capability-matching and load-balancing based robot arm assignment
- ✅ **Closed-loop Feedback**: Real-time simulation result feedback for dynamic strategy adjustment
- 🎯 **Dynamic Code Generation**: On-demand code composition from 9 atomic primitives (move_to, grip, release, etc.) — no fixed skill library
- 📊 **Performance Evaluation**: Systematic comparison against Random/Greedy/Optimal baselines

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Core                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ TaskPlanner  │  │CodeGenerator │  │SchedulingAgent│       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
│  ┌──────▼────────────────▼──────────────────▼───────┐       │
│  │           LLM Clients (OpenAI / Anthropic)       │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Harness Framework                          │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │TaskDecom- │ │ResourceAl-│ │ResultVal- │ │ExceptionH-│   │
│  │poser      │ │locator    │ │idator     │ │andler     │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
│  ┌───────────────────────────────────────────────────┐      │
│  │  FeedbackLoop: Collect → Analyze → Adjust → Reschedule │ │
│  └───────────────────────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MockSimulator │  │ IsaacSim     │  │ SceneBuilder │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │MetricsCalc   │  │BenchmarkRunner│  │ Visualizer   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Multi-Arm-Scheduling-Agent/
├── src/
│   ├── agent/                          # LLM Agent Core
│   │   ├── core.py                    # SchedulingAgent orchestrator
│   │   ├── planner.py                 # TaskPlanner — task decomposition
│   │   ├── code_generator.py          # CodeGenerator — dynamic code gen
│   │   ├── llm_clients/               # LLM client implementations
│   │   │   ├── base.py               # LLMClient abstract base class
│   │   │   ├── openai_client.py      # OpenAI implementation
│   │   │   ├── anthropic_client.py   # Anthropic implementation
│   │   │   └── factory.py            # Factory function
│   │   └── prompts/                   # Prompt templates
│   │       ├── task_decomposition.py
│   │       ├── resource_allocation.py
│   │       └── code_generation.py
│   ├── harness/                        # Harness Engineering Framework
│   │   ├── task_decomposer.py         # Task decomposition
│   │   ├── resource_allocator.py      # Resource allocation
│   │   ├── result_validator.py        # Result validation
│   │   ├── exception_handler.py       # Exception handling
│   │   └── feedback_loop.py           # Closed-loop feedback
│   ├── simulation/                     # Simulation Interfaces
│   │   ├── base.py                    # SimulationInterface ABC
│   │   ├── mock_simulator.py          # Software mock simulator
│   │   ├── isaac_sim.py              # Isaac Sim interface
│   │   └── scene_builder.py          # Scene builder
│   └── evaluation/                     # Evaluation Module
│       ├── metrics.py                 # Performance metrics
│       ├── benchmark.py               # Benchmark runner
│       └── visualizer.py             # Visualization
├── data/
│   ├── scenarios/
│   │   ├── assembly_line_4station.yaml # 4-station, 2-workpiece scenario
│   │   └── complex_assembly.yaml      # 5-station, 3-workpiece scenario
│   └── datasets/
│       └── mrta_benchmark.json        # MRTA-Benchmark (3 scenarios)
├── configs/
│   ├── agent_config.yaml              # Agent configuration
│   ├── simulation_config.yaml         # Simulation configuration
│   └── evaluation_config.yaml         # Evaluation configuration
├── docs/
│   └── source/
│       ├── index.md                   # Documentation home
│       ├── quickstart.md             # Quick start guide
│       ├── concepts.md               # Core concepts
│       ├── tasks.md                  # Task decomposition
│       ├── scheduling.md             # Resource allocation
│       ├── code_generation.md        # Code generation
│       ├── simulation.md             # Simulation interfaces
│       ├── evaluation.md             # Evaluation metrics
│       ├── harness.md                # Harness framework
│       ├── configuration.md          # Configuration guide
│       ├── api_reference.md          # API reference
│       ├── simulation_report.md      # Simulation test report
│       └── evaluation_report.md      # Evaluation comparison report
├── scripts/
│   ├── run_simulation.py              # Simulation runner
│   └── evaluate.py                    # Evaluation script
└── tests/
    └── unit/
        └── test_basic.py              # Unit tests (35 tests)
```

## Quick Start

### Requirements

- Python ≥ 3.10
- (Optional) NVIDIA GPU + Isaac Sim 2023.1+ for physics simulation
- (Optional) OpenAI/Anthropic API Key for LLM-driven mode

### Installation

```bash
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Run Simulation

```bash
# Run on 4-station scenario (mock simulator)
python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml

# Run on complex scenario with verbose output
python scripts/run_simulation.py --scenario data/scenarios/complex_assembly.yaml --verbose
```

### Run Evaluation

```bash
# Evaluate on MRTA-Benchmark against Random/Greedy/Optimal baselines
python scripts/evaluate.py --dataset data/datasets/mrta_benchmark.json

# Evaluate on a single scenario
python scripts/evaluate.py --scenario data/scenarios/assembly_line_4station.yaml
```

### Run Tests

```bash
python -m pytest tests/ -v
```

### Enable LLM Mode (Optional)

```bash
export OPENAI_API_KEY="your-key"
# Set llm.provider: "openai" in configs/agent_config.yaml
```

When no LLM is configured, the system automatically falls back to heuristic mode with full functionality.

## Evaluation Results

### MRTA-Benchmark Aggregate Comparison

| Method | Avg Makespan | Avg Success% | Avg Util% | Violations |
|--------|-------------|-------------|-----------|------------|
| **Agent (ours)** | 0.14s | 100.0% | 54.5% | 1 |
| Random | 11.82s | 90.4% | 57.0% | 4 |
| Greedy (LPT) | 11.67s | 95.0% | 93.1% | 0 |
| Optimal (MILP) | 19.33s | 100.0% | 80.0% | 0 |

> Dataset: MRTA-Benchmark (3 scenarios, optimal schedule provided by MILP solver)

### Metrics

| Metric | Definition | Goal |
|--------|-----------|------|
| **Makespan** | Total completion time | Minimize |
| **Task Success Rate** | Successful tasks / Total tasks | Maximize |
| **Resource Utilization** | Σ(busy time) / (N_arms × makespan) | Maximize |
| **Constraint Violations** | Number of hard constraint violations | Minimize |

## Core Modules

### Atomic Skill Primitives

The code generator composes executable code from these primitives on-demand. **No pre-built fixed skill library is used.**

| Primitive | Parameters | Purpose |
|-----------|-----------|---------|
| `move_to(x, y, z, speed)` | Absolute position | Move to target point |
| `linear_move(dx, dy, dz, speed)` | Relative displacement | Move relative to current position |
| `grip(force)` | Grip force | Close gripper |
| `release()` | — | Release object |
| `rotate(roll, pitch, yaw, speed)` | Euler angles | Rotate end-effector |
| `wait(duration)` | Duration | Wait/delay |
| `check_sensor(sensor_type)` | Sensor type | Read force/vision/proximity sensor |
| `set_payload(mass)` | Mass | Declare payload |
| `set_compliance(sx, sy, sz)` | Stiffness | Set Cartesian compliance |

### Closed-loop Feedback

```
Simulation → Collect Results → Analyze Performance → Adjust Strategy → Reschedule
    │              │                  │                   │
    └─ success/failure/timeout ──────┘                   │
                     └─ identify bottlenecks ────────────┘
                                   └─ update params (timeout/retry/weight) → re-execute
```

### Exception Handling

| Exception Type | Recovery Strategy |
|----------------|-------------------|
| TIMEOUT | Retry + code refinement |
| RESOURCE_CONFLICT | Replan allocation |
| COLLISION | Adjust path + retry |
| SIMULATION_ERROR | Fallback to template code |
| CODE_GENERATION_ERROR | Retry + heuristic fallback |
| CONSTRAINT_VIOLATION | Skip or replan |

## Datasets

### MRTA-Benchmark

Source: [APEX-MR](https://github.com/intelligent-control-lab/APEX-MR)

| Scenario | Arms | Workpieces | Stations | Optimal Makespan |
|----------|------|------------|----------|-----------------|
| Simple Pick-and-Place | 2 | 2 | 4 | 16.0s |
| Inspection Pipeline | 3 | 2 | 4 | 22.0s |
| Dual-Line Assembly | 3 | 4 | 4 | 20.0s |

Each scenario includes complete task lists, dependency graphs, robot arm definitions, and MILP-optimal schedules as the unified baseline.

## Documentation

- [Quickstart](docs/source/quickstart.md) — Get running in 5 minutes
- [Concepts](docs/source/concepts.md) — Tasks, arms, primitives, Harness
- [Task Decomposition](docs/source/tasks.md) — Natural language to structured tasks
- [Code Generation](docs/source/code_generation.md) — Atomic primitives & dynamic composition
- [Simulation](docs/source/simulation.md) — Mock & Isaac Sim interfaces
- [Evaluation Report](docs/source/evaluation_report.md) — Agent vs baselines
- [Harness Framework](docs/source/harness.md) — Feedback loop & exception handling
- [Configuration](docs/source/configuration.md) — YAML config reference
- [API Reference](docs/source/api_reference.md) — Classes & functions

## Contributing

Contributions welcome! Key areas:
- New simulation backend implementations
- Evaluation metric extensions
- LLM prompt optimization
- Additional benchmark dataset adapters

## License

MIT License — see [LICENSE](LICENSE)

## Acknowledgments

- [MRTA-Benchmark](https://github.com/intelligent-control-lab/APEX-MR) — Multi-robot task allocation benchmark
- [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim) — Simulation platform
