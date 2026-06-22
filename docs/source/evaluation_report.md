# Evaluation Report

## 评估设置

| 项目 | 值 |
|------|-----|
| 日期 | 2026-06-22 |
| 基准数据集 | APEX-MR (CMU, RSS 2025), 13 LEGO assembly tasks |
| 本地场景 | assembly_line_4station (4工位, 2工件, 3臂) |
| 最优基准来源 | MILP-optimal (makespan=25.0s), 明确指定于场景配置文件 |
| 基线方法 | Random, Greedy (LPT), Optimal (MILP) |
| 评估指标 | Makespan, Task Success Rate, Resource Utilization, Constraint Violations |
| 实验次数 | 3 runs (seeds: 42-44) |
| 统计方法 | Mean ± Std, Paired t-test (α=0.05) |
| LLM | Xiaomi MiMo v2.5 (mimo-v2.5) |

!!! note "最优基准说明"
    - 自定义场景 (assembly_line_4station): 最优调度由 MILP 求解器计算, makespan=25.0s
    - MRTA-Benchmark (APEX-MR) 任务: 使用论文 Table 1 报告的 makespan (来源: https://arxiv.org/abs/2503.15836)
    - 所有对比方法使用同一基准，确保公平比较

## 指标定义

| 指标 | 定义 | 目标 |
|------|------|------|
| **Makespan** | 总完工时间 (秒) | 最小化 |
| **Task Success Rate** | 成功任务 / 总任务 | 最大化 |
| **Resource Utilization** | Σ(busy_time) / (n_arms × makespan) | 最大化 |
| **Constraint Violations** | 硬约束违反次数 | 最小化 |

## 严格评估结果 (3 runs, mean ± std)

### assembly_line_4station 场景

| Metric | Agent | Greedy (LPT) | Random | Optimal (MILP) |
|--------|-------|-------------|--------|---------------|
| **Makespan** | 6.67 ± 11.55 | 17.00 ± 0.00 | 12.33 ± 1.15 | **25.00** |
| **Task Success Rate** | 33.3% ± 57.7% | 100% ± 0.0% | 100% ± 0.0% | **100%** |
| **Resource Utilization** | 22.2% ± 38.5% | 78.4% ± 0.0% | 100% ± 0.0% | **80.0%** |
| **Constraint Violations** | 0.33 ± 0.58 | 0.00 ± 0.00 | 0.00 ± 0.00 | **0** |

### 统计显著性 (paired t-test)

| Comparison | Metric | p-value | Significant |
|-----------|--------|---------|-------------|
| Agent vs Greedy | Makespan | 0.2613 | ns |
| Agent vs Random | Makespan | 0.5205 | ns |
| Agent vs Greedy | Success Rate | 0.1835 | ns |
| Agent vs Random | Success Rate | 0.1835 | ns |

> \*\*\* p<0.001, \*\* p<0.01, \* p<0.05, ns = not significant

## 分析

### 当前局限

1. **LLM规划不稳定性**: MiMo模型在任务分解(prompt较长)时偶发空响应或JSON截断,
   导致fallback到启发式方法, 产生不完整的任务集
2. **代码生成稳定**: 代码生成prompt较短, LLM响应稳定, 生成的代码可正确执行
3. **Harness闭环有效**: feedback_loop, result_validator, exception_handler 均已集成并正常工作

### 改进方向

1. 优化任务分解prompt长度, 或对长prompt使用分段策略
2. 增加LLM规划的重试+prompt重写机制
3. 扩展到更多MRTA-Benchmark任务场景
