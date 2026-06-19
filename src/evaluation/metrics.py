"""
Performance metrics for multi-arm scheduling evaluation.

Provides calculators for makespan, task success rate, resource utilization,
and constraint violations.  All functions accept an :class:`ExecutionLog`
so that metrics can be computed uniformly regardless of the simulation
backend that produced the log.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

class TaskEntryStatus(Enum):
    """Status of a task entry in the execution log."""
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskEntry:
    """Single task record in an execution log."""
    task_id: str
    arm_id: str
    start_time: float
    end_time: float
    status: str  # "completed" | "failed" | "cancelled"
    error: Optional[str] = None


@dataclass
class ExecutionLog:
    """Ordered collection of task entries produced during a run."""
    entries: List[TaskEntry] = field(default_factory=list)

    def add_entry(self, entry: TaskEntry) -> None:
        self.entries.append(entry)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)


@dataclass
class EvaluationMetrics:
    """Aggregate evaluation metrics for a single run or a summary."""
    makespan: float
    task_success_rate: float
    resource_utilization: float
    constraint_violations: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


# ------------------------------------------------------------------
# Calculator
# ------------------------------------------------------------------

class MetricsCalculator:
    """
    Compute standard scheduling metrics from an :class:`ExecutionLog`.

    All public methods are pure -- they take an *ExecutionLog* and
    return a value without side-effects.
    """

    def calculate_makespan(self, execution_log: ExecutionLog) -> float:
        """
        Makespan = latest ``end_time`` - earliest ``start_time``.

        Returns 0.0 when the log is empty.
        """
        if not execution_log.entries:
            return 0.0
        earliest = min(e.start_time for e in execution_log.entries)
        latest = max(e.end_time for e in execution_log.entries)
        makespan = latest - earliest
        logger.debug("Makespan: %.4f (earliest=%.4f, latest=%.4f)", makespan, earliest, latest)
        return makespan

    def calculate_task_success_rate(self, execution_log: ExecutionLog) -> float:
        """
        Fraction of entries whose status is ``"completed"``.

        Returns 1.0 when the log is empty (vacuously true).
        """
        if not execution_log.entries:
            return 1.0
        completed = sum(
            1 for e in execution_log.entries
            if e.status == TaskEntryStatus.COMPLETED.value or e.status == "completed"
        )
        rate = completed / len(execution_log.entries)
        logger.debug("Task success rate: %.4f (%d / %d)", rate, completed, len(execution_log))
        return rate

    def calculate_resource_utilization(
        self, execution_log: ExecutionLog, num_arms: int
    ) -> float:
        """
        Average fraction of time each arm is busy.

        Utilization = sum(task durations) / (makespan * num_arms).

        Returns 0.0 when makespan is 0 or num_arms is 0.
        """
        makespan = self.calculate_makespan(execution_log)
        if makespan <= 0.0 or num_arms <= 0:
            return 0.0

        total_busy = sum(
            e.end_time - e.start_time for e in execution_log.entries
            if e.end_time > e.start_time
        )
        utilization = total_busy / (makespan * num_arms)
        utilization = min(utilization, 1.0)
        logger.debug("Resource utilization: %.4f", utilization)
        return utilization

    def calculate_constraint_violations(self, execution_log: ExecutionLog) -> int:
        """
        Count the number of constraint violations.

        Violations detected:
        - A task's end_time < start_time (negative duration).
        - Two tasks assigned to the same arm that overlap in time
          (concurrent execution on a single arm).
        """
        violations = 0

        # Check for negative durations
        for entry in execution_log.entries:
            if entry.end_time < entry.start_time:
                violations += 1
                logger.debug(
                    "Constraint violation: negative duration for task %s", entry.task_id
                )

        # Check for overlapping tasks on the same arm
        arm_intervals: Dict[str, List[tuple]] = {}
        for entry in execution_log.entries:
            arm_intervals.setdefault(entry.arm_id, []).append(
                (entry.start_time, entry.end_time, entry.task_id)
            )
        for arm_id, intervals in arm_intervals.items():
            intervals.sort(key=lambda x: x[0])
            for i in range(len(intervals) - 1):
                if intervals[i][1] > intervals[i + 1][0]:
                    violations += 1
                    logger.debug(
                        "Constraint violation: overlap on arm %s between %s and %s",
                        arm_id,
                        intervals[i][2],
                        intervals[i + 1][2],
                    )

        return violations

    def calculate_all(
        self, execution_log: ExecutionLog, num_arms: int
    ) -> EvaluationMetrics:
        """
        Compute all metrics at once and return an :class:`EvaluationMetrics`.
        """
        makespan = self.calculate_makespan(execution_log)
        success_rate = self.calculate_task_success_rate(execution_log)
        utilization = self.calculate_resource_utilization(execution_log, num_arms)
        violations = self.calculate_constraint_violations(execution_log)

        total = len(execution_log.entries)
        completed = sum(
            1 for e in execution_log.entries
            if e.status == TaskEntryStatus.COMPLETED.value or e.status == "completed"
        )
        failed = sum(
            1 for e in execution_log.entries
            if e.status == TaskEntryStatus.FAILED.value or e.status == "failed"
        )

        metrics = EvaluationMetrics(
            makespan=makespan,
            task_success_rate=success_rate,
            resource_utilization=utilization,
            constraint_violations=violations,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
        )
        logger.info(
            "Evaluation complete: makespan=%.4f, success=%.2f%%, util=%.2f%%, violations=%d",
            makespan,
            success_rate * 100,
            utilization * 100,
            violations,
        )
        return metrics
