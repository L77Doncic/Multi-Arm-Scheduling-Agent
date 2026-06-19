# Evaluation

评估模块提供性能指标计算、基准对比和可视化功能。

## 评估指标

| 指标 | 定义 | 计算方式 | 目标 |
|------|------|----------|------|
| **Makespan** | 总完工时间 | `max(task.end_time) - min(task.start_time)` | 最小化 |
| **Task Success Rate** | 任务成功率 | `completed_tasks / total_tasks` | 最大化 |
| **Resource Utilization** | 资源利用率 | `Σ(arm_busy_time) / (n_arms × makespan)` | 最大化 |
| **Constraint Violations** | 约束违反次数 | 硬约束违反的累计次数 | 最小化 |

## MetricsCalculator

```python
from evaluation.metrics import MetricsCalculator

calc = MetricsCalculator()

# 从执行日志计算
metrics = calc.calculate_all(execution_log, num_arms=3)

print(metrics.makespan)             # 25.3
print(metrics.task_success_rate)    # 1.0
print(metrics.resource_utilization) # 0.72
print(metrics.constraint_violations) # 0
print(metrics.total_tasks)          # 8
print(metrics.completed_tasks)      # 8
```

### ExecutionLog 格式

```python
execution_log = [
    {
        "task_id": "t_001",
        "arm_id": "arm_003",
        "start_time": 1718820000.0,
        "end_time": 1718820002.1,
        "status": "completed",
        "error": None,
    },
    {
        "task_id": "t_002",
        "arm_id": "arm_001",
        "start_time": 1718820000.0,
        "end_time": 1718820008.3,
        "status": "completed",
        "error": None,
    },
    # ...
]
```

## BenchmarkRunner

### 加载MRTA-Benchmark

```python
from evaluation.benchmark import BenchmarkRunner

runner = BenchmarkRunner(config={})
scenarios = runner.load_dataset("data/datasets/mrta_benchmark.json")

for s in scenarios:
    print(f"{s.id}: {s.name} — {len(s.tasks)} tasks, optimal={s.optimal_makespan}s")
```

### 运行对比评估

```python
# 运行agent
agent_results = runner.run_benchmark(agent, scenarios)

# 生成基线
baselines = {
    "random": runner.generate_baseline_schedule(scenarios, method="random"),
    "greedy": runner.generate_baseline_schedule(scenarios, method="greedy"),
}

# 对比
report = runner.compare_with_baseline(agent_results, baselines)

print(report.agent_metrics)       # Agent的聚合指标
print(report.baseline_metrics)    # 基线的聚合指标
print(report.improvements)        # 相对改进百分比
```

### 基线方法

| 方法 | 算法 | 说明 |
|------|------|------|
| `random` | 随机分配 | 随机将任务分配给有足够能力的臂 |
| `greedy` | LPT贪心 | 按任务时长降序排列，分配给最空闲的臂 |
| `optimal` | 数据集提供 | MRTA-Benchmark中的MILP最优解 |

## 使用评估脚本

```bash
# 全量评估
python scripts/evaluate.py --dataset data/datasets/mrta_benchmark.json

# 单场景评估
python scripts/evaluate.py --scenario data/scenarios/assembly_line_4station.yaml

# 指定基线方法
python scripts/evaluate.py --dataset data/datasets/mrta_benchmark.json --baselines random,greedy

# 详细输出
python scripts/evaluate.py --dataset data/datasets/mrta_benchmark.json --verbose
```

### 输出报告

评估结果保存为JSON：

```json
{
    "agent_results": [...],
    "baseline_results": {"random": [...], "greedy": [...]},
    "agent_aggregate": {
        "avg_makespan": 0.14,
        "avg_success_rate": 1.0,
        "avg_resource_util": 0.545,
        "total_violations": 1
    },
    "baseline_aggregates": {...},
    "timestamp": "2026-06-19 21:00:00"
}
```

## Visualizer

```python
from evaluation.visualizer import Visualizer

viz = Visualizer()

# 甘特图
viz.plot_gantt_chart(execution_log, save_path="outputs/gantt.png")

# 资源利用率
viz.plot_resource_utilization(execution_log, save_path="outputs/util.png")

# Agent vs 基线对比
viz.plot_comparison(agent_metrics, baseline_metrics, save_path="outputs/compare.png")

# HTML报告
viz.generate_html_report(results, save_path="outputs/report.html")
```
