"""
Result Validator Module

This module validates execution results against a set of constraints,
covering task completion, temporal, spatial, and resource requirements.
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


class ConstraintType(Enum):
    """Constraint categories."""

    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    RESOURCE = "resource"


class Severity(Enum):
    """Violation severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Constraint:
    """A single validation constraint."""

    type: ConstraintType
    parameters: Dict[str, Any]
    severity: Severity = Severity.ERROR


@dataclass
class Violation:
    """Describes a single constraint violation."""

    constraint_type: ConstraintType
    message: str
    severity: Severity
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Aggregate result of a validation pass."""

    is_valid: bool
    violations: List[Violation]
    metrics: Dict[str, float]
    summary: str


# ------------------------------------------------------------------
# Validator
# ------------------------------------------------------------------


class ResultValidator:
    """
    Validates execution results against user-supplied constraints.

    Each ``validate`` call returns a ``ValidationResult`` that is
    ``is_valid = True`` only when *no* violations of severity ERROR or
    CRITICAL are present.
    """

    # Default thresholds (overridable via config)
    DEFAULT_MAX_DURATION_FACTOR: float = 2.0  # allowed overshoot
    DEFAULT_POSITION_TOLERANCE: float = 0.05  # metres
    DEFAULT_RESOURCE_UTILISATION_CAP: float = 1.0  # 100 %

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise the result validator.

        Args:
            config: Configuration dictionary.  Recognised keys:
                * max_duration_factor - how much over estimate is allowed
                * position_tolerance  - max positional error (metres)
                * resource_utilisation_cap - max allowable utilisation
        """
        self.config = config
        self.max_duration_factor: float = config.get(
            "max_duration_factor", self.DEFAULT_MAX_DURATION_FACTOR
        )
        self.position_tolerance: float = config.get(
            "position_tolerance", self.DEFAULT_POSITION_TOLERANCE
        )
        self.resource_utilisation_cap: float = config.get(
            "resource_utilisation_cap", self.DEFAULT_RESOURCE_UTILISATION_CAP
        )

        logger.info("ResultValidator initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        execution_result: Dict[str, Any],
        constraints: Optional[List[Constraint]] = None,
    ) -> ValidationResult:
        """
        Validate an execution result against the given constraints.

        Args:
            execution_result: Dictionary describing the execution
                outcome.  Expected keys (depending on constraint types):
                ``tasks`` (list of dicts with ``id``, ``status``,
                ``duration``), ``positions``, ``resource_usage``,
                ``total_duration``, etc.
            constraints: List of ``Constraint`` objects.  If *None* only
                task-completion validation is performed.

        Returns:
            A ``ValidationResult`` with all found violations.
        """
        if constraints is None:
            constraints = []

        violations: List[Violation] = []
        metrics: Dict[str, float] = {}

        # 1. Task completion (always checked)
        completion_ok = self._validate_task_completion(execution_result)
        metrics["task_completion"] = 1.0 if completion_ok else 0.0
        if not completion_ok:
            violations.append(
                Violation(
                    constraint_type=ConstraintType.TEMPORAL,
                    message="One or more tasks did not complete successfully",
                    severity=Severity.ERROR,
                )
            )

        # 2. Per-constraint checks
        for constraint in constraints:
            if constraint.type == ConstraintType.TEMPORAL:
                violations.extend(
                    self._validate_time_constraints(execution_result, constraint)
                )
            elif constraint.type == ConstraintType.RESOURCE:
                violations.extend(
                    self._validate_resource_constraints(execution_result, constraint)
                )
            elif constraint.type == ConstraintType.SPATIAL:
                violations.extend(
                    self._validate_spatial_constraints(execution_result, constraint)
                )
            else:
                logger.warning("Unknown constraint type: %s", constraint.type)

        # 3. Compute aggregate metrics
        metrics["violation_count"] = float(len(violations))
        critical_or_error = sum(
            1 for v in violations if v.severity in (Severity.ERROR, Severity.CRITICAL)
        )
        metrics["critical_violations"] = float(critical_or_error)

        # 4. Build result
        is_valid = critical_or_error == 0
        summary = self._build_summary(is_valid, violations, metrics)

        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            metrics=metrics,
            summary=summary,
        )

        logger.info(
            "Validation complete: valid=%s, violations=%d", is_valid, len(violations)
        )
        return result

    # ------------------------------------------------------------------
    # Internal validators
    # ------------------------------------------------------------------

    def _validate_task_completion(self, result: Dict[str, Any]) -> bool:
        """
        Check that every task in the execution result completed
        successfully.

        Returns:
            ``True`` if all tasks are complete, ``False`` otherwise.
        """
        tasks = result.get("tasks")
        if not tasks:
            logger.debug("No tasks found in execution result")
            return False

        for task in tasks:
            status = str(task.get("status", "")).lower()
            if status not in ("completed", "success", "done"):
                logger.debug(
                    "Task %s has status '%s' (expected completed)",
                    task.get("id"),
                    status,
                )
                return False

        return True

    def _validate_time_constraints(
        self,
        result: Dict[str, Any],
        constraint: Constraint,
    ) -> List[Violation]:
        """
        Validate temporal constraints.

        Supported constraint parameters:
            * ``max_total_duration`` -- hard cap on total duration.
            * ``max_task_duration``  -- per-task duration cap.
            * ``deadline``           -- absolute deadline (seconds).

        Returns:
            List of ``Violation`` objects (empty if all checks pass).
        """
        violations: List[Violation] = []
        params = constraint.parameters

        # --- Overall duration ---
        max_total = params.get("max_total_duration")
        actual_total = result.get("total_duration")
        if max_total is not None and actual_total is not None:
            if actual_total > max_total:
                violations.append(
                    Violation(
                        constraint_type=ConstraintType.TEMPORAL,
                        message=(
                            f"Total duration {actual_total:.2f}s exceeds "
                            f"maximum {max_total:.2f}s"
                        ),
                        severity=constraint.severity,
                        details={
                            "actual_duration": actual_total,
                            "max_duration": max_total,
                        },
                    )
                )

        # --- Per-task duration ---
        max_task_dur = params.get("max_task_duration")
        if max_task_dur is not None:
            for task in result.get("tasks", []):
                dur = task.get("duration")
                if dur is not None and dur > max_task_dur:
                    violations.append(
                        Violation(
                            constraint_type=ConstraintType.TEMPORAL,
                            message=(
                                f"Task {task.get('id')} duration {dur:.2f}s "
                                f"exceeds maximum {max_task_dur:.2f}s"
                            ),
                            severity=constraint.severity,
                            details={"task_id": task.get("id"), "duration": dur},
                        )
                    )

        # --- Absolute deadline ---
        deadline = params.get("deadline")
        end_time = result.get("end_time")
        if deadline is not None and end_time is not None:
            if end_time > deadline:
                violations.append(
                    Violation(
                        constraint_type=ConstraintType.TEMPORAL,
                        message=(
                            f"Execution ended at {end_time:.2f}, "
                            f"past deadline {deadline:.2f}"
                        ),
                        severity=constraint.severity,
                        details={"end_time": end_time, "deadline": deadline},
                    )
                )

        return violations

    def _validate_resource_constraints(
        self,
        result: Dict[str, Any],
        constraint: Constraint,
    ) -> List[Violation]:
        """
        Validate resource constraints.

        Supported constraint parameters:
            * ``max_utilisation`` -- per-arm utilisation cap (0-1).
            * ``max_energy``      -- total energy budget.
            * ``forbidden_arms``  -- list of arm IDs that must not be used.

        Returns:
            List of ``Violation`` objects.
        """
        violations: List[Violation] = []
        params = constraint.parameters

        # --- Per-arm utilisation ---
        max_util = params.get("max_utilisation", self.resource_utilisation_cap)
        usage = result.get("resource_usage", {})
        for arm_id, util in usage.items():
            if isinstance(util, dict):
                util = util.get("utilisation", 0.0)
            if util > max_util:
                violations.append(
                    Violation(
                        constraint_type=ConstraintType.RESOURCE,
                        message=(
                            f"Arm {arm_id} utilisation {util:.2%} "
                            f"exceeds cap {max_util:.2%}"
                        ),
                        severity=constraint.severity,
                        details={"arm_id": arm_id, "utilisation": util},
                    )
                )

        # --- Energy budget ---
        max_energy = params.get("max_energy")
        total_energy = result.get("total_energy")
        if max_energy is not None and total_energy is not None:
            if total_energy > max_energy:
                violations.append(
                    Violation(
                        constraint_type=ConstraintType.RESOURCE,
                        message=(
                            f"Total energy {total_energy:.2f} exceeds "
                            f"budget {max_energy:.2f}"
                        ),
                        severity=constraint.severity,
                        details={
                            "total_energy": total_energy,
                            "max_energy": max_energy,
                        },
                    )
                )

        # --- Forbidden arms ---
        forbidden = set(params.get("forbidden_arms", []))
        if forbidden:
            assignments = result.get("assignments", {})
            for task_id, arm_id in assignments.items():
                if arm_id in forbidden:
                    violations.append(
                        Violation(
                            constraint_type=ConstraintType.RESOURCE,
                            message=(
                                f"Task {task_id} assigned to forbidden arm {arm_id}"
                            ),
                            severity=constraint.severity,
                            details={"task_id": task_id, "arm_id": arm_id},
                        )
                    )

        return violations

    def _validate_spatial_constraints(
        self,
        result: Dict[str, Any],
        constraint: Constraint,
    ) -> List[Violation]:
        """
        Validate spatial constraints.

        Supported constraint parameters:
            * ``workspace_bounds`` -- dict with ``min_x``, ``max_x``,
              ``min_y``, ``max_y``, ``min_z``, ``max_z``.
            * ``min_arm_distance`` -- minimum distance between any two
              arms (collision avoidance).
            * ``target_positions`` -- dict of ``task_id -> (x, y, z)``
              with accepted tolerance.

        Returns:
            List of ``Violation`` objects.
        """
        violations: List[Violation] = []
        params = constraint.parameters

        # --- Workspace bounds ---
        bounds = params.get("workspace_bounds")
        if bounds:
            positions = result.get("positions", {})
            for entity_id, pos in positions.items():
                if not isinstance(pos, (list, tuple)) or len(pos) < 3:
                    continue
                x, y, z = pos[0], pos[1], pos[2]
                if (
                    x < bounds.get("min_x", -math.inf)
                    or x > bounds.get("max_x", math.inf)
                    or y < bounds.get("min_y", -math.inf)
                    or y > bounds.get("max_y", math.inf)
                    or z < bounds.get("min_z", -math.inf)
                    or z > bounds.get("max_z", math.inf)
                ):
                    violations.append(
                        Violation(
                            constraint_type=ConstraintType.SPATIAL,
                            message=(
                                f"Entity {entity_id} at ({x:.3f}, {y:.3f}, {z:.3f}) "
                                f"is outside workspace bounds"
                            ),
                            severity=constraint.severity,
                            details={"entity_id": entity_id, "position": list(pos)},
                        )
                    )

        # --- Minimum arm distance ---
        min_dist = params.get("min_arm_distance")
        if min_dist is not None:
            arm_positions = result.get("arm_positions", {})
            arm_ids = list(arm_positions.keys())
            for i in range(len(arm_ids)):
                for j in range(i + 1, len(arm_ids)):
                    p1 = arm_positions[arm_ids[i]]
                    p2 = arm_positions[arm_ids[j]]
                    dist = self._euclidean_distance(p1, p2)
                    if dist < min_dist:
                        violations.append(
                            Violation(
                                constraint_type=ConstraintType.SPATIAL,
                                message=(
                                    f"Arms {arm_ids[i]} and {arm_ids[j]} are "
                                    f"too close ({dist:.3f}m < {min_dist:.3f}m)"
                                ),
                                severity=constraint.severity,
                                details={
                                    "arm1": arm_ids[i],
                                    "arm2": arm_ids[j],
                                    "distance": dist,
                                },
                            )
                        )

        # --- Target position accuracy ---
        targets = params.get("target_positions", {})
        if targets:
            actual_positions = result.get("task_end_positions", {})
            tolerance = params.get("position_tolerance", self.position_tolerance)
            for task_id, expected in targets.items():
                actual = actual_positions.get(task_id)
                if actual is None:
                    continue
                dist = self._euclidean_distance(expected, actual)
                if dist > tolerance:
                    violations.append(
                        Violation(
                            constraint_type=ConstraintType.SPATIAL,
                            message=(
                                f"Task {task_id} end position off by "
                                f"{dist:.4f}m (tolerance {tolerance:.4f}m)"
                            ),
                            severity=constraint.severity,
                            details={
                                "task_id": task_id,
                                "expected": list(expected),
                                "actual": list(actual),
                                "offset": dist,
                            },
                        )
                    )

        return violations

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _euclidean_distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
        """Compute Euclidean distance between two points."""
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    @staticmethod
    def _build_summary(
        is_valid: bool,
        violations: List[Violation],
        metrics: Dict[str, float],
    ) -> str:
        """Build a human-readable summary string."""
        status = "PASS" if is_valid else "FAIL"
        n = len(violations)
        if n == 0:
            return f"Validation {status}: all checks passed"
        by_severity: Dict[str, int] = {}
        for v in violations:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
        detail = ", ".join(f"{k}={v}" for k, v in sorted(by_severity.items()))
        return f"Validation {status}: {n} violation(s) [{detail}]"
