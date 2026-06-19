# Quickstart

本指南帮助你在5分钟内安装并运行多机械臂调度系统。

## 环境要求

| 要求 | 说明 |
|------|------|
| Python | ≥ 3.10 |
| **GPU** | **NVIDIA RTX 3070+ (8GB+ VRAM)** — Isaac Sim仿真需要 |
| NVIDIA Driver | 535+ |
| OS | Ubuntu 20.04/22.04 或 Windows 10/11 |
| RAM | 32GB+ (推荐64GB) |

!!! warning "GPU是必需的"
    任务要求接入Isaac Sim进行仿真验证。Isaac Sim基于Omniverse平台，**必须使用NVIDIA RTX GPU**。
    GTX系列、集成显卡、AMD显卡均不支持。

    无GPU时可用MockSimulator进行开发调试，但无法完成物理仿真验证。
    也可使用云端GPU实例（AWS EC2 G5、Google Cloud A2 等）。

## 安装

### 从源码安装

```bash
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
pip install -e .
```

### 依赖

| 包 | 用途 | 必需 |
|----|------|------|
| pyyaml | 配置文件解析 | ✅ |
| numpy, scipy | 数值计算 | ✅ |
| matplotlib | 可视化 | ✅ |
| networkx | 依赖图 | ✅ |
| openai | OpenAI LLM客户端 | 可选 |
| anthropic | Anthropic LLM客户端 | 可选 |

!!! tip
    不安装 `openai` / `anthropic` 也能运行。系统会自动回退到启发式模式，所有功能可用。

## 运行仿真

```bash
# 4工位产线场景
python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml

# 复杂场景 + 详细日志
python scripts/run_simulation.py --scenario data/scenarios/complex_assembly.yaml --verbose
```

输出示例：

```
======================================================================
SIMULATION RESULTS
======================================================================
Execution ID:    5bdf620b
Tasks:           8
Makespan:        0.00s
Success Rate:    100.0%
Resource Util:   6.7%
Violations:      0

TASK DETAILS:
----------------------------------------------------------------------
  ✓ t_001  | pick_workpiece_from_feed_wp_A  | arm=arm_003 | completed
  ✓ t_002  | assemble_components_wp_A       | arm=arm_001 | completed
  ✓ t_003  | quality_inspection_wp_A        | arm=arm_003 | completed
  ✓ t_004  | package_and_output_wp_A        | arm=arm_001 | completed
  ...
```

## 下载MRTA-Benchmark数据集（可选）

评估需要真实工业数据集时，下载 APEX-MR 的 LEGO 组装任务：

```bash
python scripts/download_dataset.py
```

这会将13个LEGO组装任务文件下载到 `data/datasets/MRTA-Benchmark/`。

或手动下载：

```bash
git clone --depth 1 https://github.com/intelligent-control-lab/APEX-MR.git /tmp/APEX-MR
mkdir -p data/datasets/MRTA-Benchmark
cp /tmp/APEX-MR/config/lego_tasks/assembly_tasks/*.json data/datasets/MRTA-Benchmark/
```

> 数据集文件不会提交到git（外部依赖，需用户自行下载）。

## 运行评估

```bash
# MRTA-Benchmark全量评估（需先下载数据集）
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark

# 单场景评估（无需下载数据集）
python scripts/evaluate.py --scenario data/scenarios/assembly_line_4station.yaml
```

输出示例：

```
================================================================================
EVALUATION REPORT
================================================================================
Dataset: data/datasets/mrta_benchmark.json
Scenarios: 3

Method         Makespan   Success%      Util%   Violations
--------------------------------------------------------
Agent              0.14      100.0       54.5            1
random            11.82       90.4       57.0            4
greedy            11.67       95.0       93.1            0
optimal           19.33      100.0       80.0            0
```

## 启用LLM模式（可选）

配置API密钥后，系统将使用LLM进行任务规划和代码生成：

```bash
# 方式一：环境变量
export OPENAI_API_KEY="sk-..."

# 方式二：修改配置文件
# configs/agent_config.yaml
# llm:
#   provider: "openai"
#   model: "gpt-4-turbo"
```

支持的LLM提供商：

| 提供商 | 配置 `llm.provider` | 需要的环境变量 |
|--------|-------------------|---------------|
| OpenAI | `"openai"` | `OPENAI_API_KEY` |
| Anthropic | `"anthropic"` | `ANTHROPIC_API_KEY` |

## Python API 使用

```python
import yaml
from agent.core import SchedulingAgent

# 加载配置
with open("configs/agent_config.yaml") as f:
    config = yaml.safe_load(f)

# 创建智能体
agent = SchedulingAgent(config)

# 定义场景
scene = {
    "stations": [
        {"id": "s1", "operation": "pick", "capabilities_required": ["pick"],
         "estimated_duration": 2.0, "predecessors": [], "successors": ["s2"]},
        {"id": "s2", "operation": "assemble", "capabilities_required": ["assemble"],
         "estimated_duration": 5.0, "predecessors": ["s1"], "successors": []},
    ],
    "workpieces": [
        {"id": "wp_A", "operations_sequence": ["s1", "s2"], "priority": 1},
    ],
}

# 执行调度
result = agent.execute_scheduling(
    instruction="Pick workpiece A and assemble it",
    scene_config=scene,
)

# 查看结果
print(f"Tasks: {len(result.tasks)}")
print(f"Success rate: {result.task_success_rate:.0%}")
print(f"Allocation: {result.allocation}")
```

## 运行测试

```bash
python -m pytest tests/ -v
```

```
tests/unit/test_basic.py::TestTaskStatus::test_values PASSED
tests/unit/test_basic.py::TestSchedulingAgent::test_execute_scheduling PASSED
tests/unit/test_basic.py::TestCodeGenerator::test_code_is_valid_python PASSED
...
35 passed in 0.13s
```

## 下一步

- [Concepts](concepts.md) — 了解核心概念
- [Task Decomposition](tasks.md) — 深入任务分解
- [Configuration](configuration.md) — 完整配置说明
