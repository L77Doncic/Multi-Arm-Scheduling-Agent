# Quickstart

本指南帮助你在 5 分钟内安装并运行多机械臂调度系统。

## 环境要求

| 要求 | Mock 仿真（默认） | Isaac Sim 仿真 |
|------|:-----------------:|:--------------:|
| Python | ≥ 3.10 | ≥ 3.10 |
| GPU | ❌ 不需要 | ✅ NVIDIA RTX 3070+ |
| CUDA | 不需要 | ≥ 11.7 |
| RAM | 8GB+ | 32GB+ |
| OS | Linux / macOS / Windows | Ubuntu 20.04/22.04 |

> [!TIP]
> **不需要 GPU 也能完整运行系统**。默认使用 Mock 仿真器，所有功能（LLM 调度、代码生成、闭环反馈、评估）均可使用。GPU 仅在需要物理级仿真（碰撞检测、力学模拟）时必需。

## 安装

```bash
# 克隆仓库
git clone https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent.git
cd Multi-Arm-Scheduling-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

## 运行第一个仿真

```bash
# 使用 Mock 仿真器（默认，无需 GPU）
python scripts/run_simulation.py --scenario data/scenarios/assembly_line_4station.yaml
```

<details>
<summary>📖 预期输出</summary>

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
  ✓ t_004  | Transport workpiece A         | arm=arm_001 | completed
  ✓ t_005  | Inspect workpiece A           | arm=arm_003 | completed
  ...
```
</details>

## 使用 LLM 增强（可选）

系统默认使用 ModelScope API 调用 DeepSeek-V4-Flash 模型。配置在 `configs/agent_config.yaml`：

```yaml
llm:
  provider: "openai"
  model: "deepseek-ai/DeepSeek-V4-Flash"
  api_base: "https://api-inference.modelscope.cn/v1"
  api_key_env: "OPENAI_API_KEY"    # 从环境变量读取密钥
```

设置 API 密钥：

```bash
# 方式一：环境变量
export OPENAI_API_KEY="your-api-key"

# 方式二：.env 文件
cp .env.example .env
# 编辑 .env 填入密钥
```

> [!NOTE]
> 无 LLM API Key 时，系统自动回退到启发式任务分解 + 模板代码生成，所有功能仍可用。

## 运行评估

```bash
# 严格评估（5 次运行，配对 t 检验，NeurIPS 标准）
python scripts/evaluate_rigorous.py \
    --scenario data/scenarios/assembly_line_4station.yaml \
    --runs 5

# MRTA-Benchmark 数据集评估
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark
```

<details>
<summary>📖 评估输出示例</summary>

```
==========================================================================================
RIGOROUS EVALUATION RESULTS (mean ± std)
==========================================================================================

Metric                          Agent       Greedy(LPT)            Random
------------------------------------------------------------------------------------------
makespan                     20.000 ± 0.000    17.000 ± 0.000    12.333 ± 1.155
task_success_rate             1.000 ± 0.000     1.000 ± 0.000     1.000 ± 0.000
resource_utilization          0.667 ± 0.000     0.784 ± 0.000     0.957 ± 0.096
constraint_violations         1.000 ± 0.000     0.000 ± 0.000     0.000 ± 0.000

Statistical Significance (paired t-test, α=0.05):
  makespan          vs Greedy(LPT):  p=0.0000 ***
  makespan          vs Random:       p=0.0003 ***
```
</details>

## Python API 使用

```python
import yaml
from agent.core import SchedulingAgent

# 1. 加载配置
config = yaml.safe_load(open("configs/agent_config.yaml"))

# 2. 加载场景
scene = yaml.safe_load(open("data/scenarios/assembly_line_4station.yaml"))["scenario"]
config["robot_arms"] = scene["robot_arms"]

# 3. 创建智能体
agent = SchedulingAgent(config)

# 4. 执行调度
result = agent.execute_scheduling(
    instruction=scene["instruction"],
    scene_config=scene,
)

# 5. 查看结果
print(f"Tasks: {len(result.tasks)}")
print(f"Makespan: {result.makespan:.1f}s")
print(f"Success rate: {result.task_success_rate:.0%}")
print(f"Allocation: {result.allocation}")
print(f"Feedback adjustments: {len(result.feedback_adjustments)}")
```

## 下一步

- [Concepts](concepts.md) — 了解核心概念
- [Task Decomposition](tasks.md) — 深入任务分解
- [Harness Framework](harness.md) — 闭环反馈机制
- [Configuration](configuration.md) — 完整配置说明
