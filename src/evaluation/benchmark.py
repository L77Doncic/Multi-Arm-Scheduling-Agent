"""
Benchmark runner for multi-arm scheduling evaluation.

Supports loading scenario datasets (MRTA-Benchmark format), running an
agent against those scenarios, and comparing the results with baseline
scheduling strategies (random, greedy, genetic).
"""

import json
import logging
import math
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence

from evaluation.metrics import (
    EvaluationMetrics,
    ExecutionLog,
    MetricsCalculator,
    TaskEntry,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Protocols / minimal interfaces
# ------------------------------------------------------------------

class AgentProtocol(Protocol):
    """Minimal interface that an agent must satisfy to be benchmarked."""

    def execute_scheduling(self, instruction: str) -> Dict[str, Any]:
        """Return a dict that includes at least an ``execution_log`` key."""
        ...


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class Scenario:
    """A single benchmarking scenario."""
    instruction: str
    config: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[Dict[str, Any]] = None


@dataclass
class BenchmarkResult:
    """Result of running an agent over a set of scenarios."""
    scenarios: List[Scenario]
    metrics_list: List[EvaluationMetrics]
    aggregate_metrics: EvaluationMetrics


@dataclass
class ComparisonReport:
    """Comparison of agent metrics against a baseline."""
    agent_metrics: EvaluationMetrics
    baseline_metrics: EvaluationMetrics
    improvements: Dict[str, float]
    statistical_significance: Dict[str, float]  # metric -> p-value (placeholder)


# ------------------------------------------------------------------
# Schedule helpers
# ------------------------------------------------------------------

@dataclass
class Schedule:
    """A simple schedule mapping tasks to (arm_id, start, end)."""
    assignments: List[Dict[str, Any]] = field(default_factory=list)


def _execution_log_from_schedule(schedule: Schedule) -> ExecutionLog:
    """Convert a Schedule into an ExecutionLog for metric calculation."""
    log = ExecutionLog()
    for a in schedule.assignments:
        log.add_entry(
            TaskEntry(
                task_id=a["task_id"],
                arm_id=a["arm_id"],
                start_time=a["start_time"],
                end_time=a["end_time"],
                status=a.get("status", "completed"),
                error=a.get("error"),
            )
        )
    return log


# ------------------------------------------------------------------
# Benchmark runner
# ------------------------------------------------------------------

class BenchmarkRunner:
    """
    Run an agent against benchmark scenarios and compare with baselines.
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)
        self._calculator = MetricsCalculator()

    # ------------------------------------------------------------------
    # Dataset loading
    # ------------------------------------------------------------------

    def load_dataset(self, dataset_path: str) -> List[Scenario]:
        """
        Load benchmark scenarios from a JSON file.

        The expected JSON structure follows the MRTA-Benchmark format::

            {
              "scenarios": [
                {
                  "instruction": "Assemble two widgets ...",
                  "config": { ... },
                  "expected_result": { ... }
                },
                ...
              ]
            }

        A directory containing multiple JSON files is also accepted --
        each file is loaded and the lists are concatenated.
        """
        path = Path(dataset_path)
        scenarios: List[Scenario] = []

        if path.is_dir():
            json_files = sorted(path.glob("*.json"))
            for jf in json_files:
                scenarios.extend(self._load_single_file(jf))
            logger.info("Loaded %d scenarios from %d files in %s", len(scenarios), len(json_files), path)
        elif path.is_file():
            scenarios = self._load_single_file(path)
            logger.info("Loaded %d scenarios from %s", len(scenarios), path)
        else:
            raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

        return scenarios

    def _load_single_file(self, filepath: Path) -> List[Scenario]:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        raw_scenarios = data.get("scenarios", [])
        scenarios: List[Scenario] = []
        for raw in raw_scenarios:
            scenarios.append(
                Scenario(
                    instruction=raw["instruction"],
                    config=raw.get("config", {}),
                    expected_result=raw.get("expected_result"),
                )
            )
        return scenarios

    # ------------------------------------------------------------------
    # Run benchmark
    # ------------------------------------------------------------------

    def run_benchmark(
        self,
        agent: AgentProtocol,
        scenarios: List[Scenario],
        num_arms: int = 2,
    ) -> BenchmarkResult:
        """
        Execute *agent* on each scenario and collect metrics.

        Args:
            agent: Object with an ``execute_scheduling(instruction)`` method.
            scenarios: List of benchmark scenarios.
            num_arms: Number of robot arms (for resource-utilization calc).

        Returns:
            A :class:`BenchmarkResult` with per-scenario and aggregate metrics.
        """
        metrics_list: List[EvaluationMetrics] = []
        for idx, scenario in enumerate(scenarios):
            logger.info(
                "Running scenario %d/%d: %s",
                idx + 1,
                len(scenarios),
                scenario.instruction[:80],
            )
            try:
                result = agent.execute_scheduling(scenario.instruction)
                exec_log: ExecutionLog = result.get("execution_log", ExecutionLog())
                m = self._calculator.calculate_all(exec_log, num_arms)
            except Exception as exc:
                logger.error("Scenario %d failed: %s", idx, exc, exc_info=True)
                m = EvaluationMetrics(
                    makespan=0.0,
                    task_success_rate=0.0,
                    resource_utilization=0.0,
                    constraint_violations=0,
                    total_tasks=0,
                    completed_tasks=0,
                    failed_tasks=0,
                )
            metrics_list.append(m)

        aggregate = self._aggregate_metrics(metrics_list)
        return BenchmarkResult(
            scenarios=scenarios,
            metrics_list=metrics_list,
            aggregate_metrics=aggregate,
        )

    def _aggregate_metrics(self, metrics_list: List[EvaluationMetrics]) -> EvaluationMetrics:
        if not metrics_list:
            return EvaluationMetrics(0, 0, 0, 0, 0, 0, 0)
        n = len(metrics_list)
        return EvaluationMetrics(
            makespan=sum(m.makespan for m in metrics_list) / n,
            task_success_rate=sum(m.task_success_rate for m in metrics_list) / n,
            resource_utilization=sum(m.resource_utilization for m in metrics_list) / n,
            constraint_violations=sum(m.constraint_violations for m in metrics_list),
            total_tasks=sum(m.total_tasks for m in metrics_list),
            completed_tasks=sum(m.completed_tasks for m in metrics_list),
            failed_tasks=sum(m.failed_tasks for m in metrics_list),
        )

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare_with_baseline(
        self,
        results: BenchmarkResult,
        baseline: BenchmarkResult,
    ) -> ComparisonReport:
        """
        Compute per-metric improvements and a simple significance test.

        Improvements are expressed as ``(baseline - agent) / baseline``
        for cost-like metrics (makespan, violations) and
        ``(agent - baseline) / baseline`` for rate-like metrics
        (success rate, utilization).
        """
        am = results.aggregate_metrics
        bm = baseline.aggregate_metrics

        def _pct_change(agent_val: float, base_val: float, lower_is_better: bool) -> float:
            if base_val == 0:
                return 0.0
            diff = (base_val - agent_val) if lower_is_better else (agent_val - base_val)
            return diff / abs(base_val)

        improvements = {
            "makespan": _pct_change(am.makespan, bm.makespan, lower_is_better=True),
            "task_success_rate": _pct_change(am.task_success_rate, bm.task_success_rate, lower_is_better=False),
            "resource_utilization": _pct_change(am.resource_utilization, bm.resource_utilization, lower_is_better=False),
            "constraint_violations": _pct_change(
                float(am.constraint_violations),
                float(bm.constraint_violations),
                lower_is_better=True,
            ),
        }

        # Simple paired t-test placeholder (requires scipy for real use)
        significance = self._compute_significance(results.metrics_list, baseline.metrics_list)

        return ComparisonReport(
            agent_metrics=am,
            baseline_metrics=bm,
            improvements=improvements,
            statistical_significance=significance,
        )

    def _compute_significance(
        self,
        agent_metrics: List[EvaluationMetrics],
        baseline_metrics: List[EvaluationMetrics],
    ) -> Dict[str, float]:
        """
        Compute a paired t-test p-value for each metric.

        Falls back to a normal-approximation when scipy is unavailable.
        """
        try:
            from scipy import stats  # type: ignore[import-untyped]

            def _paired_p(agent_vals: List[float], base_vals: List[float]) -> float:
                if len(agent_vals) < 2:
                    return 1.0
                _, p = stats.ttest_rel(agent_vals, base_vals)
                return float(p)

        except ImportError:
            logger.debug("scipy not installed; using normal approximation for p-values")

            def _paired_p(agent_vals: List[float], base_vals: List[float]) -> float:
                n = len(agent_vals)
                if n < 2:
                    return 1.0
                diffs = [a - b for a, b in zip(agent_vals, base_vals)]
                mean_d = sum(diffs) / n
                var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
                se = math.sqrt(var_d / n) if var_d > 0 else 1e-9
                z = abs(mean_d / se)
                # Two-tailed normal approximation
                p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(z / math.sqrt(2))))
                return p

        agent_makespans = [m.makespan for m in agent_metrics]
        baseline_makespans = [m.makespan for m in baseline_metrics]

        agent_success = [m.task_success_rate for m in agent_metrics]
        baseline_success = [m.task_success_rate for m in baseline_metrics]

        agent_util = [m.resource_utilization for m in agent_metrics]
        baseline_util = [m.resource_utilization for m in baseline_metrics]

        agent_violations = [float(m.constraint_violations) for m in agent_metrics]
        baseline_violations = [float(m.constraint_violations) for m in baseline_metrics]

        return {
            "makespan": _paired_p(agent_makespans, baseline_makespans),
            "task_success_rate": _paired_p(agent_success, baseline_success),
            "resource_utilization": _paired_p(agent_util, baseline_util),
            "constraint_violations": _paired_p(agent_violations, baseline_violations),
        }

    # ------------------------------------------------------------------
    # Baseline schedule generators
    # ------------------------------------------------------------------

    def generate_baseline_schedule(
        self,
        scenarios: List[Scenario],
        method: str = "greedy",
    ) -> List[Schedule]:
        """
        Generate baseline schedules for a list of scenarios.

        Args:
            scenarios: The scenarios to schedule.
            method: One of ``"random"``, ``"greedy"``, ``"genetic"``.

        Returns:
            One :class:`Schedule` per scenario.

        Raises:
            ValueError: If *method* is not recognised.
        """
        generators: Dict[str, Callable[[Scenario], Schedule]] = {
            "random": self._schedule_random,
            "greedy": self._schedule_greedy,
            "genetic": self._schedule_genetic,
        }
        generator = generators.get(method)
        if generator is None:
            raise ValueError(
                f"Unknown baseline method '{method}'; choose from {list(generators)}"
            )

        schedules: List[Schedule] = []
        for scenario in scenarios:
            schedules.append(generator(scenario))
        logger.info("Generated %d baseline schedules using '%s'", len(schedules), method)
        return schedules

    # -- random baseline --------------------------------------------------

    def _schedule_random(self, scenario: Scenario) -> Schedule:
        cfg = scenario.config
        num_tasks = cfg.get("num_tasks", 5)
        num_arms = cfg.get("num_arms", 2)
        task_duration = cfg.get("task_duration", 2.0)

        assignments: List[Dict[str, Any]] = []
        time = 0.0
        for t in range(num_tasks):
            arm_id = f"arm_{self._rng.randint(0, num_arms - 1)}"
            dur = task_duration * self._rng.uniform(0.5, 1.5)
            assignments.append({
                "task_id": f"task_{t}",
                "arm_id": arm_id,
                "start_time": time,
                "end_time": time + dur,
                "status": "completed",
            })
            time += dur * 0.5  # some overlap potential
        return Schedule(assignments=assignments)

    # -- greedy baseline --------------------------------------------------

    def _schedule_greedy(self, scenario: Scenario) -> Schedule:
        cfg = scenario.config
        num_tasks = cfg.get("num_tasks", 5)
        num_arms = cfg.get("num_arms", 2)
        task_duration = cfg.get("task_duration", 2.0)

        # Greedy: always assign to the arm that becomes free soonest
        arm_free_at: List[float] = [0.0] * num_arms
        assignments: List[Dict[str, Any]] = []
        for t in range(num_tasks):
            arm_idx = min(range(num_arms), key=lambda i: arm_free_at[i])
            start = arm_free_at[arm_idx]
            end = start + task_duration
            assignments.append({
                "task_id": f"task_{t}",
                "arm_id": f"arm_{arm_idx}",
                "start_time": start,
                "end_time": end,
                "status": "completed",
            })
            arm_free_at[arm_idx] = end
        return Schedule(assignments=assignments)

    # -- genetic baseline -------------------------------------------------

    def _schedule_genetic(self, scenario: Scenario, generations: int = 50) -> Schedule:
        cfg = scenario.config
        num_tasks = cfg.get("num_tasks", 5)
        num_arms = cfg.get("num_arms", 2)
        task_duration = cfg.get("task_duration", 2.0)
        pop_size = 30

        def _random_chromosome() -> List[int]:
            return [self._rng.randint(0, num_arms - 1) for _ in range(num_tasks)]

        def _fitness(chrom: List[int]) -> float:
            # Simulate sequential scheduling per arm, return negative makespan
            arm_free = [0.0] * num_arms
            for t, arm_idx in enumerate(chrom):
                arm_free[arm_idx] = arm_free[arm_idx] + task_duration
            return -max(arm_free)  # lower makespan is better

        def _crossover(a: List[int], b: List[int]) -> List[int]:
            pt = self._rng.randint(1, num_tasks - 1) if num_tasks > 1 else 1
            return a[:pt] + b[pt:]

        def _mutate(chrom: List[int], rate: float = 0.1) -> List[int]:
            return [
                self._rng.randint(0, num_arms - 1) if self._rng.random() < rate else g
                for g in chrom
            ]

        # Initialise population
        population = [_random_chromosome() for _ in range(pop_size)]

        for _ in range(generations):
            scored = [(c, _fitness(c)) for c in population]
            scored.sort(key=lambda x: x[1], reverse=True)
            survivors = [c for c, _ in scored[:pop_size // 2]]
            children: List[List[int]] = []
            while len(children) < pop_size - len(survivors):
                p1, p2 = self._rng.sample(survivors, 2)
                child = _mutate(_crossover(p1, p2))
                children.append(child)
            population = survivors + children

        best = max(population, key=_fitness)

        # Build schedule from best chromosome
        arm_free = [0.0] * num_arms
        assignments: List[Dict[str, Any]] = []
        for t, arm_idx in enumerate(best):
            start = arm_free[arm_idx]
            end = start + task_duration
            assignments.append({
                "task_id": f"task_{t}",
                "arm_id": f"arm_{arm_idx}",
                "start_time": start,
                "end_time": end,
                "status": "completed",
            })
            arm_free[arm_idx] = end
        return Schedule(assignments=assignments)
