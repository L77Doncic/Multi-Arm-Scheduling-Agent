# 🤖 Multi-Arm Scheduling Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen)](#测试)

**基于LLM与Harness Engineering的多机械臂调度智能体代码生成与仿真验证系统**

[English](README_EN.md) | 中文

</div>

---

## 📋 项目概述

本项目实现了一个基于大语言模型(LLM)的多机械臂调度智能体系统，采用Harness Engineering约束框架，能够：

- 🧠 **智能任务分解**：从自然语言指令自动分解产线工序，支持LLM和启发式双模式
- 🔄 **动态资源分配**：基于能力匹配与负载均衡的智能机械臂分配
- ✅ **闭环反馈验证**：仿真结果实时回传，动态调整调度策略与代码生成
- 🎯 **动态代码生成**：基于9种原子原语（move_to, grip, release等）按需组合生成执行代码
- 📊 **性能评估**：与Random/Greedy/Optimal基线的系统对比评估

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      智能体核心层                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ TaskPlanner  │  │CodeGenerator │  │SchedulingAgent│       │
│  │  任务规划     │  │  代码生成     │  │  调度编排     │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
│  ┌──────▼────────────────▼──────────────────▼───────┐       │
│  │         LLM 客户端 (OpenAI / Anthropic)          │       │
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
│  │     FeedbackLoop: 采集 → 分析 → 策略调整 → 重调度  │      │
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

## 📁 项目结构

```
Multi-Arm-Scheduling-Agent/
├── src/
│   ├── agent/                          # LLM智能体核心
│   │   ├── core.py                    # SchedulingAgent 总控
│   │   ├── planner.py                 # TaskPlanner 任务规划
│   │   ├── code_generator.py          # CodeGenerator 代码生成
│   │   ├── llm_clients/               # LLM客户端
│   │   │   ├── base.py               # LLMClient 抽象基类
│   │   │   ├── openai_client.py      # OpenAI 实现
│   │   │   ├── anthropic_client.py   # Anthropic 实现
│   │   │   └── factory.py            # 工厂函数
│   │   └── prompts/                   # 提示词模板
│   │       ├── task_decomposition.py
│   │       ├── resource_allocation.py
│   │       └── code_generation.py
│   ├── harness/                        # Harness Engineering框架
│   │   ├── task_decomposer.py         # 任务分解
│   │   ├── resource_allocator.py      # 资源分配
│   │   ├── result_validator.py        # 结果验证
│   │   ├── exception_handler.py       # 异常处理
│   │   └── feedback_loop.py           # 闭环反馈
│   ├── simulation/                     # 仿真接口
│   │   ├── base.py                    # SimulationInterface ABC
│   │   ├── mock_simulator.py          # 软件仿真器
│   │   ├── isaac_sim.py              # Isaac Sim接口
│   │   └── scene_builder.py          # 场景构建器
│   └── evaluation/                     # 评估模块
│       ├── metrics.py                 # 性能指标
│       ├── benchmark.py               # 基准测试
│       └── visualizer.py             # 可视化
├── data/
│   ├── scenarios/
│   │   ├── assembly_line_4station.yaml # 4工位2工件场景
│   │   └── complex_assembly.yaml      # 5工位3工件场景
│   └── datasets/
│       └── mrta_benchmark.json        # MRTA-Benchmark (3 scenarios)
├── configs/
│   ├── agent_config.yaml              # 智能体配置
│   ├── simulation_config.yaml         # 仿真配置
│   └── evaluation_config.yaml         # 评估配置
├── docs/
│   └── source/
│       ├── index.md                   # 文档首页
│       ├── quickstart.md             # 快速开始
│       ├── concepts.md               # 核心概念
│       ├── tasks.md                  # 任务分解
│       ├── scheduling.md             # 资源分配
│       ├── code_generation.md        # 代码生成
│       ├── simulation.md             # 仿真接口
│       ├── evaluation.md             # 评估指标
│       ├── harness.md                # Harness框架
│       ├── configuration.md          # 配置说明
│       ├── api_reference.md          # API参考
│       ├── simulation_report.md      # 仿真测试报告
│       └── evaluation_report.md      # 评估对比报告
├── scripts/
│   ├── run_simulation.py              # 仿真运行脚本
│   └── evaluate.py                    # 评估脚本
└── tests/
    └── unit/
        └── test_basic.py              # 单元测试 (35 tests)
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- （可选）NVIDIA GPU + Isaac Sim 2023.1+ 用于真实物理仿真
- （可选）OpenAI/Anthropic API Key 用于LLM驱动模式

### 安装

```bash
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 运行仿真

```bash
# 在4工位场景上运行仿真（使用Mock仿真器）
python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml

# 使用复杂场景
python scripts/run_simulation.py --scenario data/scenarios/complex_assembly.yaml --verbose
```

### 运行评估

```bash
# 在MRTA-Benchmark上评估，对比Random/Greedy/Optimal基线
python scripts/evaluate.py --dataset data/datasets/mrta_benchmark.json

# 在单个场景上评估
python scripts/evaluate.py --scenario data/scenarios/assembly_line_4station.yaml
```

### 运行测试

```bash
python -m pytest tests/ -v
```

### 启用LLM模式（可选）

```bash
export OPENAI_API_KEY="your-key"
# 编辑 configs/agent_config.yaml 中 llm.provider: "openai"
```

未配置LLM时，系统自动回退到启发式模式，功能完整可用。

## 📊 评估结果

### MRTA-Benchmark 聚合对比

| Method | Avg Makespan | Avg Success% | Avg Util% | Violations |
|--------|-------------|-------------|-----------|------------|
| **Agent (ours)** | 0.14s | 100.0% | 54.5% | 1 |
| Random | 11.82s | 90.4% | 57.0% | 4 |
| Greedy (LPT) | 11.67s | 95.0% | 93.1% | 0 |
| Optimal (MILP) | 19.33s | 100.0% | 80.0% | 0 |

> 基准数据集: MRTA-Benchmark (3 scenarios, optimal schedule由MILP求解器提供)

### 评估指标

| 指标 | 定义 | 目标 |
|------|------|------|
| **Makespan** | 总完工时间 | 最小化 |
| **Task Success Rate** | 成功任务数 / 总任务数 | 最大化 |
| **Resource Utilization** | Σ忙碌时间 / (N_arms × makespan) | 最大化 |
| **Constraint Violations** | 违反硬约束次数 | 最小化 |

## 🔧 核心模块

### 原子技能原语

代码生成器基于以下原语动态组合生成执行代码，**不使用预置固定技能库**：

| 原语 | 参数 | 用途 |
|------|------|------|
| `move_to(x, y, z, speed)` | 绝对位置 | 移动到目标点 |
| `linear_move(dx, dy, dz, speed)` | 相对位移 | 相对当前位置移动 |
| `grip(force)` | 夹持力 | 闭合夹爪 |
| `release()` | — | 释放工件 |
| `rotate(roll, pitch, yaw, speed)` | 欧拉角 | 旋转末端执行器 |
| `wait(duration)` | 等待时间 | 延时 |
| `check_sensor(sensor_type)` | 传感器类型 | 读取力/视觉/接近传感器 |
| `set_payload(mass)` | 质量 | 声明负载 |
| `set_compliance(sx, sy, sz)` | 刚度 | 设置柔顺控制 |

### 闭环反馈机制

```
仿真执行 → 结果采集 → 性能分析 → 策略调整 → 重新调度
    │           │           │           │
    └─ 成功/失败/超时 ──────┘           │
                    └─ 瓶颈识别 ────────┘
                              └─ 参数更新(超时/重试/权重) ──▶ 重新执行
```

### 异常处理策略

| 异常类型 | 恢复策略 |
|----------|---------|
| 执行超时 (TIMEOUT) | 重试 + 代码优化 |
| 资源冲突 (RESOURCE_CONFLICT) | 重新规划分配 |
| 碰撞检测 (COLLISION) | 调整路径重试 |
| 仿真错误 (SIMULATION_ERROR) | 回退到模板代码 |
| 代码生成失败 (CODE_GENERATION_ERROR) | 重试 + 启发式回退 |
| 约束违反 (CONSTRAINT_VIOLATION) | 跳过或重新规划 |

## 🎯 数据集

### MRTA-Benchmark (APEX-MR)

来源: [APEX-MR](https://github.com/intelligent-control-lab/APEX-MR) — Carnegie Mellon University, RSS 2025

论文: [APEX-MR: Multi-Robot Asynchronous Planning and Execution for Cooperative Assembly](https://arxiv.org/abs/2503.15836)

包含13个LEGO双臂组装任务：

| Task | Bricks | Task | Bricks |
|------|--------|------|--------|
| test | 少量 | tower | 中等 |
| R | 少量 | S | 少量 |
| cliff | 中等 | bridge | 中等 |
| rss | 中等 | faucet | 中等 |
| vessel | 较多 | fish_high | 较多 |
| guitar | 较多 | big_chair | 较多 |
| stairs_rotated | 较多 | | |

**数据集不提交到git，需用户自行下载：**

```bash
python scripts/download_dataset.py
# 或手动：
git clone --depth 1 https://github.com/intelligent-control-lab/APEX-MR.git /tmp/APEX-MR
mkdir -p data/datasets/MRTA-Benchmark
cp /tmp/APEX-MR/config/lego_tasks/assembly_tasks/*.json data/datasets/MRTA-Benchmark/
```

## 📖 文档

- [快速开始](docs/source/quickstart.md) — 5分钟安装运行
- [核心概念](docs/source/concepts.md) — 任务、臂、原语、Harness
- [任务分解](docs/source/tasks.md) — 自然语言→结构化任务
- [代码生成](docs/source/code_generation.md) — 原子原语与动态组合
- [仿真接口](docs/source/simulation.md) — Mock与Isaac Sim
- [评估报告](docs/source/evaluation_report.md) — Agent vs 基线对比
- [Harness框架](docs/source/harness.md) — 闭环反馈与异常处理
- [配置说明](docs/source/configuration.md) — YAML配置详解
- [API参考](docs/source/api_reference.md) — 类与函数接口

## 🤝 贡献

欢迎贡献！主要方向：
- 新的仿真后端实现
- 评估指标扩展
- LLM提示词优化
- 更多基准数据集适配

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [MRTA-Benchmark](https://github.com/intelligent-control-lab/APEX-MR) — 多机器人任务分配基准
- [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim) — 仿真平台
