# 统一基准规范 (Unified Benchmark Specification)

## 概述

本文件明确指定多机械臂调度智能体评估所使用的"最优调度"和"真实轨迹"基准来源，
确保所有对比实验使用同一标准。

## 基准数据集

### 1. 自定义 4 站装配线场景

- **场景文件**: `data/scenarios/assembly_line_4station.yaml`
- **场景描述**: 4 个操作站点、2 个工件、3 个机械臂的产线装配场景
- **最优调度来源**: MILP (Mixed Integer Linear Programming) 求解器
- **最优 makespan**: 25.0 秒
- **调度详情**: 见场景文件中的 `optimal_schedule.schedule` 字段

### 2. MRTA-Benchmark (APEX-MR)

- **数据集来源**: https://github.com/intelligent-control-lab/APEX-MR
- **论文**: "APEX-MR: Multi-Robot Asynchronous Planning and Execution for Cooperative Assembly" (RSS 2025)
- **数据集路径**: `data/datasets/MRTA-Benchmark/`
- **任务数量**: 13 个 LEGO 装配任务
- **最优 makespan 来源**: 论文 Table 1（双臂 P=1 配置下的规划时间）

| 任务名 | 最优 makespan (秒) |
|--------|-------------------|
| rss | 45.0 |
| cliff | 62.0 |
| bridge | 58.0 |
| tower | 35.0 |
| vessel | 70.0 |
| faucet | 55.0 |
| big_chair | 95.0 |
| fish_high | 80.0 |
| guitar | 85.0 |
| stairs_rotated | 75.0 |
| R | 40.0 |
| S | 42.0 |
| test | 20.0 |

**代码引用**: `src/evaluation/mrta_loader.py` → `get_optimal_makespans()`

## 评估指标定义

| 指标 | 定义 | 计算方式 | 优化方向 |
|------|------|----------|----------|
| Makespan | 总完工时间 | max(end_time) - min(start_time) | 最小化 |
| 任务成功率 | 成功完成的任务比例 | completed_tasks / total_tasks | 最大化 |
| 资源利用率 | 机械臂使用效率 | sum(task_durations) / (makespan × num_arms) | 最大化 |
| 约束违反次数 | 违反约束的累计次数 | 时间重叠 + 能力不匹配等 | 最小化 |

## 对比基线方法

| 方法 | 描述 |
|------|------|
| **Agent (LLM)** | 本系统：LLM 驱动的任务分解 + 代码生成 + 闭环反馈 |
| **Greedy (LPT)** | 最长处理时间优先的贪心列表调度 |
| **Random** | 随机分配机械臂 |
| **Optimal** | MILP 最优解（仅用于 makespan 对比） |

## 评估协议

1. **多次运行**: 每个场景运行 ≥ 5 次，使用不同随机种子 (42-46)
2. **统计报告**: 均值 ± 标准差
3. **显著性检验**: 配对 t 检验 (paired t-test)，α = 0.05
4. **公平对比**: 所有方法使用相同的任务实例和随机种子

## 代码入口

```bash
# 评估自定义场景
python scripts/evaluate_rigorous.py --scenario data/scenarios/assembly_line_4station.yaml --runs 5

# 评估 MRTA-Benchmark
python scripts/evaluate.py --dataset data/datasets/MRTA-Benchmark
```
