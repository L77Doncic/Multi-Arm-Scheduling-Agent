"""
Feedback Loop Module

This module implements a closed-loop feedback mechanism that collects
execution results, analyses performance, and adjusts scheduling
strategy parameters accordingly.
"""

import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class FeedbackData:
    """Raw feedback collected from a single task execution."""

    timestamp: float
    task_id: str
    arm_id: str
    status: str  # "success", "failure", "timeout", etc.
    duration: float
    resource_usage: Dict[str, float]
    errors: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Outcome of analysing a batch of feedback data."""

    performance_score: float  # 0.0 - 1.0
    bottlenecks: List[str]  # human-readable bottleneck descriptions
    recommendations: List[str]  # actionable recommendations


@dataclass
class StrategyAdjustment:
    """A single parameter adjustment recommended by the feedback loop."""

    target_module: str
    parameter: str
    old_value: Any
    new_value: Any
    reason: str


# ------------------------------------------------------------------
# Adjustable strategy parameters
# ------------------------------------------------------------------


class StrategyParameter(Enum):
    """Names of strategy parameters that can be adjusted."""

    TIMEOUT_ADJUSTMENT = "timeout_adjustment"
    RETRY_COUNT = "retry_count"
    RESOURCE_WEIGHT = "resource_weight"
    PRIORITY_BOOST = "priority_boost"
    CODE_GEN_SPEED_FACTOR = "code_gen_speed_factor"
    CODE_GEN_FORCE_FACTOR = "code_gen_force_factor"


# ------------------------------------------------------------------
# Feedback loop
# ------------------------------------------------------------------


class FeedbackLoop:
    """
    Closed-loop feedback mechanism.

    Collects per-task feedback, analyses aggregated performance, and
    proposes strategy adjustments.  Maintains a full adjustment history
    so callers can inspect or roll back changes.
    """

    # Default strategy bounds (parameter -> (min, max))
    _PARAM_BOUNDS: Dict[str, tuple] = {
        StrategyParameter.TIMEOUT_ADJUSTMENT.value: (0.5, 5.0),
        StrategyParameter.RETRY_COUNT.value: (1, 10),
        StrategyParameter.RESOURCE_WEIGHT.value: (0.0, 1.0),
        StrategyParameter.PRIORITY_BOOST.value: (0.0, 2.0),
        StrategyParameter.CODE_GEN_SPEED_FACTOR.value: (0.1, 3.0),
        StrategyParameter.CODE_GEN_FORCE_FACTOR.value: (0.5, 3.0),
    }

    # Default strategy values
    _DEFAULT_STRATEGY: Dict[str, float] = {
        StrategyParameter.TIMEOUT_ADJUSTMENT.value: 1.0,
        StrategyParameter.RETRY_COUNT.value: 3.0,
        StrategyParameter.RESOURCE_WEIGHT.value: 0.5,
        StrategyParameter.PRIORITY_BOOST.value: 0.0,
        StrategyParameter.CODE_GEN_SPEED_FACTOR.value: 1.0,
        StrategyParameter.CODE_GEN_FORCE_FACTOR.value: 1.0,
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise the feedback loop.

        Args:
            config: Configuration dictionary.  Recognised keys:
                * feedback_window   -- number of recent entries used for
                  analysis (default 100)
                * adjustment_threshold -- minimum performance delta that
                  triggers an adjustment (default 0.05)
                * strategy          -- initial strategy parameter overrides
        """
        self.config = config
        self.feedback_window: int = config.get("feedback_window", 100)
        self.adjustment_threshold: float = config.get("adjustment_threshold", 0.05)

        # Current strategy parameters (mutable)
        self._strategy: Dict[str, float] = dict(self._DEFAULT_STRATEGY)
        for k, v in config.get("strategy", {}).items():
            if k in self._strategy:
                self._strategy[k] = float(v)

        # Feedback buffer and adjustment history
        self._feedback_buffer: List[FeedbackData] = []
        self._adjustment_history: List[StrategyAdjustment] = []

        logger.info("FeedbackLoop initialised with strategy %s", self._strategy)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_feedback(self, execution_result: Dict[str, Any]) -> FeedbackData:
        """
        Collect feedback from an execution result and store it.

        Args:
            execution_result: Dictionary produced by the executor.  Expected
                keys: ``task_id``, ``arm_id``, ``status``, ``duration``,
                ``resource_usage``, ``errors``.

        Returns:
            The ``FeedbackData`` record that was stored.
        """
        data = FeedbackData(
            timestamp=time.time(),
            task_id=execution_result.get("task_id", "unknown"),
            arm_id=execution_result.get("arm_id", "unknown"),
            status=str(execution_result.get("status", "unknown")),
            duration=float(execution_result.get("duration", 0.0)),
            resource_usage=dict(execution_result.get("resource_usage", {})),
            errors=list(execution_result.get("errors", [])),
        )

        self._feedback_buffer.append(data)

        # Keep buffer within window
        if len(self._feedback_buffer) > self.feedback_window:
            overflow = len(self._feedback_buffer) - self.feedback_window
            self._feedback_buffer = self._feedback_buffer[overflow:]

        logger.debug(
            "Collected feedback for task %s (status=%s, duration=%.2f)",
            data.task_id,
            data.status,
            data.duration,
        )
        return data

    def analyze_feedback(
        self, feedback: Optional[List[FeedbackData]] = None
    ) -> AnalysisResult:
        """
        Analyse collected feedback and produce an ``AnalysisResult``.

        Args:
            feedback: Explicit list of feedback records.  If *None* the
                internal buffer is used.

        Returns:
            An ``AnalysisResult`` with a performance score (0-1),
            bottleneck descriptions, and recommendations.
        """
        if feedback is None:
            feedback = list(self._feedback_buffer)

        if not feedback:
            return AnalysisResult(
                performance_score=1.0,
                bottlenecks=[],
                recommendations=["No feedback data available"],
            )

        # --- Performance score ---
        success_count = sum(
            1 for f in feedback if f.status in ("success", "completed", "done")
        )
        success_rate = success_count / len(feedback)

        durations = [f.duration for f in feedback if f.duration > 0]
        avg_duration = statistics.mean(durations) if durations else 0.0
        duration_variance = (
            statistics.pvariance(durations) if len(durations) > 1 else 0.0
        )

        # Penalise high variance (jitter is bad for scheduling)
        variance_penalty = min(duration_variance / (avg_duration + 1e-6), 1.0) * 0.2

        performance_score = max(0.0, min(1.0, success_rate - variance_penalty))

        # --- Bottlenecks ---
        bottlenecks: List[str] = []

        # Identify arms with low success rates
        arm_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "success": 0}
        )
        for f in feedback:
            arm_stats[f.arm_id]["total"] += 1
            if f.status in ("success", "completed", "done"):
                arm_stats[f.arm_id]["success"] += 1
        for arm_id, stats in arm_stats.items():
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
            if rate < 0.7:
                bottlenecks.append(f"Arm {arm_id} has low success rate ({rate:.0%})")

        # Identify tasks with excessive duration
        if durations:
            mean_dur = statistics.mean(durations)
            for f in feedback:
                if f.duration > mean_dur * 2:
                    bottlenecks.append(
                        f"Task {f.task_id} on arm {f.arm_id} took "
                        f"{f.duration:.1f}s (avg {mean_dur:.1f}s)"
                    )

        # Identify common error patterns
        error_counts: Dict[str, int] = defaultdict(int)
        for f in feedback:
            for err in f.errors:
                error_counts[err] += 1
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:3]:
            if count >= 2:
                bottlenecks.append(f"Recurring error ({count}x): {err}")

        # --- Recommendations ---
        recommendations: List[str] = []

        if success_rate < 0.9:
            recommendations.append(
                "Consider increasing retry_count to improve success rate"
            )

        if duration_variance > avg_duration * 0.5 and avg_duration > 0:
            recommendations.append(
                "High duration variance detected; consider adjusting "
                "timeout_adjustment or re-balancing workload"
            )

        overloaded_arms = [
            arm_id
            for arm_id, stats in arm_stats.items()
            if stats["total"] > len(feedback) * 0.5
        ]
        if overloaded_arms:
            recommendations.append(
                f"Arms {', '.join(overloaded_arms)} are overloaded; "
                f"increase resource_weight to favour better distribution"
            )

        if not recommendations:
            recommendations.append("Performance is within acceptable bounds")

        return AnalysisResult(
            performance_score=performance_score,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

    def adjust_strategy(
        self, analysis: Optional[AnalysisResult] = None
    ) -> List[StrategyAdjustment]:
        """
        Propose strategy adjustments based on the latest analysis.

        Args:
            analysis: Pre-computed analysis.  If *None* one is derived
                from the current feedback buffer.

        Returns:
            List of ``StrategyAdjustment`` objects (may be empty if no
            change is warranted).
        """
        if analysis is None:
            analysis = self.analyze_feedback()

        adjustments: List[StrategyAdjustment] = []

        # --- Adjust timeout ---
        if analysis.performance_score < 0.8:
            old_val = self._strategy[StrategyParameter.TIMEOUT_ADJUSTMENT.value]
            new_val = self._clamp(
                StrategyParameter.TIMEOUT_ADJUSTMENT.value,
                old_val * 1.2,
            )
            if abs(new_val - old_val) > self.adjustment_threshold:
                adj = StrategyAdjustment(
                    target_module="resource_allocator",
                    parameter=StrategyParameter.TIMEOUT_ADJUSTMENT.value,
                    old_value=old_val,
                    new_value=new_val,
                    reason=(
                        f"Low performance score ({analysis.performance_score:.2f}); "
                        f"increasing timeout factor"
                    ),
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_val

        # --- Adjust retry count ---
        if any("success rate" in b.lower() for b in analysis.bottlenecks):
            old_val = self._strategy[StrategyParameter.RETRY_COUNT.value]
            new_val = self._clamp(
                StrategyParameter.RETRY_COUNT.value,
                old_val + 1,
            )
            if new_val != old_val:
                adj = StrategyAdjustment(
                    target_module="exception_handler",
                    parameter=StrategyParameter.RETRY_COUNT.value,
                    old_value=old_val,
                    new_value=new_val,
                    reason="Low arm success rate detected; increasing retries",
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_val

        # --- Adjust resource weight ---
        if any("overloaded" in r.lower() for r in analysis.recommendations):
            old_val = self._strategy[StrategyParameter.RESOURCE_WEIGHT.value]
            new_val = self._clamp(
                StrategyParameter.RESOURCE_WEIGHT.value,
                old_val + 0.1,
            )
            if abs(new_val - old_val) > self.adjustment_threshold:
                adj = StrategyAdjustment(
                    target_module="resource_allocator",
                    parameter=StrategyParameter.RESOURCE_WEIGHT.value,
                    old_value=old_val,
                    new_value=new_val,
                    reason="Arm overload detected; increasing resource weight for better distribution",
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_val

        # --- Adjust priority boost for frequently failing tasks ---
        error_tasks = self._identify_error_prone_tasks()
        if error_tasks:
            old_val = self._strategy[StrategyParameter.PRIORITY_BOOST.value]
            new_val = self._clamp(
                StrategyParameter.PRIORITY_BOOST.value,
                old_val + 0.1,
            )
            if abs(new_val - old_val) > self.adjustment_threshold:
                adj = StrategyAdjustment(
                    target_module="resource_allocator",
                    parameter=StrategyParameter.PRIORITY_BOOST.value,
                    old_value=old_val,
                    new_value=new_val,
                    reason=(
                        f"Error-prone tasks identified: "
                        f"{', '.join(error_tasks[:3])}; boosting priority"
                    ),
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_val

        # --- Adjust code generation parameters on failures ---
        failure_count = sum(
            1
            for fb in self._feedback_buffer
            if fb.status not in ("success", "completed", "done")
        )
        total_count = len(self._feedback_buffer)
        if total_count > 0 and failure_count / total_count > 0.2:
            # Slow down movements to reduce execution errors
            old_speed = self._strategy[
                StrategyParameter.CODE_GEN_SPEED_FACTOR.value
            ]
            new_speed = self._clamp(
                StrategyParameter.CODE_GEN_SPEED_FACTOR.value,
                old_speed * 0.8,
            )
            if abs(new_speed - old_speed) > self.adjustment_threshold:
                adj = StrategyAdjustment(
                    target_module="code_generator",
                    parameter=StrategyParameter.CODE_GEN_SPEED_FACTOR.value,
                    old_value=old_speed,
                    new_value=new_speed,
                    reason=(
                        f"High failure rate ({failure_count}/{total_count}); "
                        f"slowing generated code movements"
                    ),
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_speed

            # Increase grip force to improve pick reliability
            old_force = self._strategy[
                StrategyParameter.CODE_GEN_FORCE_FACTOR.value
            ]
            new_force = self._clamp(
                StrategyParameter.CODE_GEN_FORCE_FACTOR.value,
                old_force * 1.15,
            )
            if abs(new_force - old_force) > self.adjustment_threshold:
                adj = StrategyAdjustment(
                    target_module="code_generator",
                    parameter=StrategyParameter.CODE_GEN_FORCE_FACTOR.value,
                    old_value=old_force,
                    new_value=new_force,
                    reason=(
                        f"High failure rate ({failure_count}/{total_count}); "
                        f"increasing grip force in generated code"
                    ),
                )
                adjustments.append(adj)
                self._strategy[adj.parameter] = new_force

        self._adjustment_history.extend(adjustments)

        if adjustments:
            logger.info("Strategy adjusted: %d change(s)", len(adjustments))
        else:
            logger.debug("No strategy adjustments needed")

        return adjustments

    def get_adjustment_history(self) -> List[StrategyAdjustment]:
        """
        Return the full history of strategy adjustments.

        Returns:
            List of ``StrategyAdjustment`` objects in chronological order.
        """
        return list(self._adjustment_history)

    def get_current_strategy(self) -> Dict[str, float]:
        """Return a copy of the current strategy parameters."""
        return dict(self._strategy)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clamp(self, parameter: str, value: float) -> float:
        """Clamp *value* to the configured bounds for *parameter*."""
        lo, hi = self._PARAM_BOUNDS.get(parameter, (0.0, 100.0))
        return max(lo, min(hi, value))

    def _identify_error_prone_tasks(self) -> List[str]:
        """
        Identify tasks that have failed more than once in the recent
        feedback buffer.
        """
        failure_counts: Dict[str, int] = defaultdict(int)
        for fb in self._feedback_buffer:
            if fb.status not in ("success", "completed", "done"):
                failure_counts[fb.task_id] += 1
        return [task_id for task_id, count in failure_counts.items() if count > 1]
