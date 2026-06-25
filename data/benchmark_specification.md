# 统一基准规范 (Unified Benchmark Specification)

## 概述

本文件明确指定多机械臂调度智能体评估所使用的"最优调度"和"真实轨迹"基准来源，
确保所有对比实验使用同一标准。

## 基准数据集

### MRTA-Benchmark (Sadcher/TU Delft)

- **数据集来源**: TU Delft MSc Robotics, Autonomous Multi-Robot Lab
- **原始数据**: 250K 个 MILP 最优求解的多机器人任务分配实例
- **求解方法**: MILP (Mixed Integer Linear Programming) 使用 PuLP + CBC solver
- **数据集路径**: `data/datasets/MRTA-Benchmark/`
- **场景数量**: 6 个产线场景（从 250K 实例中选取代表性样本）
- **每个场景**: 4 个操作节点 + 2 个工件 + 3 个机械臂
- **最优 makespan 来源**: MILP 求解器生成的最优调度（每个场景独立求解）

| 场景 | 来源实例 | 最优 makespan (秒) | 优先约束数 | Agent μ (秒) | Agent σ |
|------|---------|-------------------|-----------|-------------|---------|
| 1p_production_line | problem_instance_1p_017145 | 584.9 | 1 | 146.9 | 133.5 |
| 2p_production_line | problem_instance_2p_050465 | 931.0 | 2 | 76.5 | 75.2 |
| 3p_production_line | problem_instance_3p_096969 | 642.8 | 3 | 152.2 | 95.9 |
| 4p_production_line | problem_instance_4p_146259 | 465.0 | 4 | 101.8 | 75.1 |
| 5p_production_line | problem_instance_5p_182974 | 490.9 | 5 | 174.3 | 171.4 |
| 6p_production_line | problem_instance_6p_217821 | 489.8 | 6 | 336.7 | 29.1 |

**产线节点映射**:
- Station 1 (Feed): 取件/上料
- Station 2 (Transport): 搬运/传输
- Station 3 (Assembly): 组装/加工
- Station 4 (Inspection): 检测/质检

## 评估指标定义

| 指标 | 定义 | 计算方式 | 优化方向 |
|------|------|----------|----------|
| Makespan | 总完工时间 | max(end_time) - min(start_time) | 最小化 |
| 任务成功率 | 成功完成的任务比例 | completed_tasks / total_tasks | 最大化 |
| 资源利用率 | 机械臂使用效率 | sum(task_durations) / (makespan × num_arms) | 最大化 |
| 约束违反次数 | 违反约束的累计次数 | 时间重叠 + 能力不匹配等 | 最小化 |

## 对比基线方法

| 方法 | 描述 | 基准来源 |
|------|------|---------|
| **Agent (LLM)** | 本系统：LLM 驱动的任务分解 + 代码生成 + 闭环反馈 | — |
| **MILP-Optimal** | 混合整数线性规划最优解 | 数据集自带 |

## 评估协议

1. **多次运行**: 每个场景运行 5 次，使用不同随机种子 (42-46)
2. **统计报告**: 均值 ± 标准差
3. **显著性检验**: 配对 t 检验 (paired t-test)，α = 0.05
4. **公平对比**: 所有方法使用相同的任务实例和随机种子

## 实验结果摘要

- **总实验数**: 30 (6 场景 × 5 种子，seed=42-46)
- **LLM**: DeepSeek Chat（替代 mimo-v2.5，因长 prompt 超时）
- **仿真后端**: PhysXOnlySimulator（纯物理计算 + MRTA 旅行时间，无 Vulkan 渲染）
- **平均 makespan**: 682.9 秒
- **平均比率**: 1.19x（相对于 MILP 最优解）
- **成功率**: 80%
- **平均资源利用率**: 47%
- **约束违反**: 0 次（大多数场景）

### 各场景结果

| 场景 | Makespan | 最优 Makespan | 比率 | 成功率 | 利用率 |
|------|:--------:|:------------:|:----:|:------:|:------:|
| 1p | 704.6s | 584.9s | 1.20x | 80% | 44% |
| 2p | 684.9s | 931.0s | 0.74x | 80% | 47% |
| 3p | 854.1s | 642.8s | 1.33x | 72% | 47% |
| 4p | 739.5s | 465.0s | 1.59x | 82% | 40% |
| 5p | 654.0s | 490.9s | 1.33x | 80% | 50% |
| 6p | 460.1s | 489.8s | 0.94x | 88% | 57% |

## 代码入口

```bash
# 运行全部实验
python scripts/run_all_experiments.py

# 运行单个实验
python scripts/_run_single.py data/scenarios/1p_production_line.json 42 outputs/experiments
```
