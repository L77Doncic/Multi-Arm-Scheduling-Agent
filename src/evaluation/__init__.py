"""
Evaluation package for multi-arm scheduling.

Exports
-------
Metrics:
    MetricsCalculator, EvaluationMetrics, ExecutionLog, TaskEntry

Benchmarking:
    BenchmarkRunner, Scenario, BenchmarkResult, ComparisonReport

Visualization:
    Visualizer
"""

from evaluation.benchmark import (
    BenchmarkResult,
    BenchmarkRunner,
    ComparisonReport,
    Scenario,
)
from evaluation.metrics import (
    EvaluationMetrics,
    ExecutionLog,
    MetricsCalculator,
    TaskEntry,
)

# Visualizer requires matplotlib — lazy import to avoid hard dependency
try:
    from evaluation.visualizer import Visualizer
except ImportError:
    Visualizer = None  # type: ignore[misc,assignment]

__all__ = [
    # metrics
    "MetricsCalculator",
    "EvaluationMetrics",
    "ExecutionLog",
    "TaskEntry",
    # benchmark
    "BenchmarkRunner",
    "Scenario",
    "BenchmarkResult",
    "ComparisonReport",
    # visualization
    "Visualizer",
]
