# 🤖 Multi-Arm Scheduling Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/L77Doncic/Multi-Arm-Scheduling-Agent?style=social)](https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent/stargazers)

**基于LLM与Harness Engineering的多机械臂调度智能体代码生成与仿真验证系统**

*An LLM-driven multi-arm scheduling agent with harness engineering constraints for industrial automation*

[English](#english) | [中文](#中文)

</div>

---

## 📋 项目概述

本项目实现了一个基于大语言模型(LLM)的多机械臂调度智能体系统，采用Harness Engineering约束框架，能够：

- 🧠 **智能任务分解**：从自然语言指令自动分解产线工序
- 🔄 **动态资源分配**：基于LLM的智能机械臂分配与调度
- ✅ **闭环反馈验证**：仿真结果实时回传，动态调整策略
- 🎯 **代码自动生成**：为每个机械臂生成可执行行为代码
- 📊 **性能评估**：全面的评估指标与基准对比

## 🏗️ 系统架构

```
Multi-Arm-Scheduling-Agent/
├── src/                          # 源代码目录
│   ├── agent/                    # LLM智能体核心
│   │   ├── __init__.py
│   │   ├── core.py              # 智能体核心逻辑
│   │   ├── planner.py           # 任务规划器
│   │   ├── code_generator.py    # 代码生成器
│   │   └── prompt_templates/    # 提示词模板
│   ├── harness/                  # Harness Engineering框架
│   │   ├── __init__.py
│   │   ├── task_decomposer.py   # 任务分解模块
│   │   ├── resource_allocator.py # 资源分配模块
│   │   ├── result_validator.py  # 结果验证模块
│   │   ├── exception_handler.py # 异常处理模块
│   │   └── feedback_loop.py     # 闭环反馈机制
│   ├── simulation/               # 仿真接口
│   │   ├── __init__.py
│   │   ├── isaac_sim.py         # Isaac Sim接口
│   │   ├── omniverse.py         # Omniverse接口
│   │   ├── isaac_lab.py         # Isaac Lab接口
│   │   └── scene_builder.py     # 场景构建器
│   └── evaluation/               # 评估模块
│       ├── __init__.py
│       ├── metrics.py           # 评估指标
│       ├── benchmark.py         # 基准测试
│       └── visualizer.py        # 可视化工具
├── configs/                      # 配置文件
│   ├── agent_config.yaml        # 智能体配置
│   ├── simulation_config.yaml   # 仿真配置
│   └── evaluation_config.yaml   # 评估配置
├── docs/                         # 文档
│   ├── design/                  # 设计文档
│   │   ├── architecture.md      # 系统架构设计
│   │   ├── harness_design.md    # Harness框架设计
│   │   └── api_reference.md     # API参考文档
│   └── reports/                 # 测试报告
│       ├── simulation_report.md # 仿真测试报告
│       └── evaluation_report.md # 评估对比报告
├── tests/                        # 测试代码
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
├── scripts/                      # 脚本工具
│   ├── setup.sh                 # 环境设置脚本
│   ├── run_simulation.py        # 仿真运行脚本
│   └── evaluate.py              # 评估脚本
├── data/                         # 数据目录
│   ├── datasets/                # 数据集
│   └── scenarios/               # 场景配置
├── outputs/                      # 输出目录
│   ├── videos/                  # 仿真视频
│   ├── logs/                    # 运行日志
│   └── results/                 # 评估结果
├── requirements.txt              # Python依赖
├── setup.py                      # 安装配置
├── .gitignore                    # Git忽略文件
└── LICENSE                       # MIT许可证
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- NVIDIA GPU (推荐RTX 3080或更高)
- CUDA ≥ 11.7
- Isaac Sim 2023.1+ 或 Isaac Lab

### 安装

```bash
# 克隆仓库
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

### 配置

1. 配置LLM API密钥：
```bash
export OPENAI_API_KEY="your-api-key"
# 或
export ANTHROPIC_API_KEY="your-api-key"
```

2. 配置仿真环境：
```bash
# 编辑 configs/simulation_config.yaml
vim configs/simulation_config.yaml
```

### 运行示例

```bash
# 运行完整仿真流程
python scripts/run_simulation.py --scenario data/scenarios/assembly_line.yaml

# 运行评估
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark
```

## 📊 评估指标

系统评估包含以下核心指标：

| 指标 | 描述 | 计算方式 |
|------|------|----------|
| **Makespan** | 总完工时间 | 最后任务完成时间 - 开始时间 |
| **任务成功率** | 成功完成的任务比例 | 成功任务数 / 总任务数 |
| **资源利用率** | 机械臂使用效率 | 忙碌时间 / 总时间 |
| **约束违反次数** | 违反约束的次数 | 累计违反次数 |

## 🎯 数据集支持

系统支持以下开源工业数据集：

- **MRTA-Benchmark**: 多机器人任务分配基准数据集
- **哈工大工业智能数据集**: 云边端协同测试验证数据集
- **自定义场景**: 支持用户自定义产线场景

## 🔧 Harness Engineering框架

### 核心模块

1. **任务分解模块** (`task_decomposer.py`)
   - 自然语言指令解析
   - 工序自动分解
   - 依赖关系分析

2. **资源分配模块** (`resource_allocator.py`)
   - 机械臂能力评估
   - 动态负载均衡
   - 冲突检测与解决

3. **结果验证模块** (`result_validator.py`)
   - 仿真结果验证
   - 约束满足检查
   - 性能指标计算

4. **异常处理模块** (`exception_handler.py`)
   - 异常检测
   - 自动恢复策略
   - 错误报告生成

5. **闭环反馈机制** (`feedback_loop.py`)
   - 实时结果回传
   - 策略动态调整
   - 持续优化

## 📹 仿真演示

<div align="center">

![仿真演示](docs/assets/simulation_demo.gif)

*多机械臂协同装配仿真演示*

</div>

## 🤝 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 贡献领域

- 🔧 新的仿真接口实现
- 📊 评估指标扩展
- 🐛 Bug修复与性能优化
- 📖 文档完善与翻译
- 🎨 可视化工具增强

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [OpenHarness](https://github.com/HKUDS/OpenHarness) - Harness Engineering架构参考
- [MRTA-Benchmark](https://github.com/intelligent-control-lab/APEX-MR) - 多机器人任务分配基准
- [Isaac Sim](https://developer.nvidia.com/isaac-sim) - NVIDIA仿真平台

## 📧 联系方式

- 项目主页: [GitHub](https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent)
- 问题反馈: [Issues](https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent/issues)
- 讨论交流: [Discussions](https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent/discussions)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！⭐**

</div>

<a name="english"></a>
## English

### Overview

This project implements an LLM-driven multi-arm scheduling agent system using Harness Engineering constraints framework. It features:

- 🧠 **Intelligent Task Decomposition**: Automatic process decomposition from natural language instructions
- 🔄 **Dynamic Resource Allocation**: LLM-based intelligent arm allocation and scheduling
- ✅ **Closed-loop Feedback Verification**: Real-time simulation result feedback with dynamic strategy adjustment
- 🎯 **Automatic Code Generation**: Generate executable behavior code for each robotic arm
- 📊 **Performance Evaluation**: Comprehensive evaluation metrics and benchmark comparison

### Key Features

1. **LLM-Powered Scheduling**: Leverages large language models for intelligent decision-making
2. **Harness Engineering Framework**: Implements closed-loop feedback with task decomposition, resource allocation, result verification, and exception handling
3. **Simulation Integration**: Supports Isaac Sim, Omniverse, and Isaac Lab interfaces
4. **Comprehensive Evaluation**: Makespan, task success rate, resource utilization, and constraint violation metrics

### Quick Start

```bash
# Clone repository
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

# Setup environment
./scripts/setup.sh

# Run simulation
python scripts/run_simulation.py --scenario data/scenarios/assembly_line.yaml
```

### Architecture

The system follows a modular architecture with four main components:

1. **Agent Module**: LLM-based intelligent agent for task planning and code generation
2. **Harness Module**: Constraint framework with feedback loop
3. **Simulation Module**: Integration with NVIDIA Isaac ecosystem
4. **Evaluation Module**: Performance metrics and benchmarking

See [docs/design/architecture.md](docs/design/architecture.md) for detailed architecture documentation.
