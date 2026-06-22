"""
Exception Handler Module

This module classifies exceptions that occur during scheduling and
execution, determines appropriate recovery actions, and maintains
statistics for adaptive behaviour.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Enums & data classes
# ------------------------------------------------------------------


class ExceptionType(Enum):
    """Categories of exceptions the system can handle."""
    TIMEOUT = "timeout"
    RESOURCE_CONFLICT = "resource_conflict"
    COLLISION = "collision"
    COMMUNICATION_FAILURE = "communication_failure"
    SIMULATION_ERROR = "simulation_error"
    CODE_GENERATION_ERROR = "code_generation_error"
    CONSTRAINT_VIOLATION = "constraint_violation"


class RecoveryActionType(Enum):
    """High-level recovery strategies."""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    REPLAN = "replan"


@dataclass
class RecoveryAction:
    """Describes a recommended recovery action."""
    action_type: RecoveryActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # higher = more urgent


@dataclass
class ExceptionRecord:
    """Historical record of a handled exception."""
    timestamp: float
    exception_type: ExceptionType
    message: str
    recovery: RecoveryAction
    outcome: str  # "success", "failure", "partial"
    context: Dict[str, Any] = field(default_factory=dict)


class ExceptionHandler:
    """
    Classifies exceptions, selects recovery strategies, and tracks
    statistics to inform future decisions.
    """

    # Default retry limits per exception type
    _DEFAULT_MAX_RETRIES: Dict[ExceptionType, int] = {
        ExceptionType.TIMEOUT: 3,
        ExceptionType.RESOURCE_CONFLICT: 2,
        ExceptionType.COLLISION: 1,
        ExceptionType.COMMUNICATION_FAILURE: 5,
        ExceptionType.SIMULATION_ERROR: 2,
        ExceptionType.CODE_GENERATION_ERROR: 3,
        ExceptionType.CONSTRAINT_VIOLATION: 1,
    }

    # Default recovery mapping (used when context is insufficient)
    _DEFAULT_RECOVERY: Dict[ExceptionType, RecoveryActionType] = {
        ExceptionType.TIMEOUT: RecoveryActionType.RETRY,
        ExceptionType.RESOURCE_CONFLICT: RecoveryActionType.REPLAN,
        ExceptionType.COLLISION: RecoveryActionType.REPLAN,
        ExceptionType.COMMUNICATION_FAILURE: RecoveryActionType.RETRY,
        ExceptionType.SIMULATION_ERROR: RecoveryActionType.FALLBACK,
        ExceptionType.CODE_GENERATION_ERROR: RecoveryActionType.RETRY,
        ExceptionType.CONSTRAINT_VIOLATION: RecoveryActionType.REPLAN,
    }

    # Priority levels per exception type (higher = more urgent)
    _DEFAULT_PRIORITY: Dict[ExceptionType, int] = {
        ExceptionType.COLLISION: 100,
        ExceptionType.CONSTRAINT_VIOLATION: 90,
        ExceptionType.RESOURCE_CONFLICT: 80,
        ExceptionType.TIMEOUT: 60,
        ExceptionType.SIMULATION_ERROR: 50,
        ExceptionType.CODE_GENERATION_ERROR: 40,
        ExceptionType.COMMUNICATION_FAILURE: 30,
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, config: Dict[str, Any]):
        """
        Initialise the exception handler.

        Args:
            config: Configuration dictionary.  Recognised keys:
                * max_retries        -- per-type retry overrides
                * recovery_overrides -- per-type action overrides
                * history_limit      -- max records to keep (default 1000)
        """
        self.config = config
        self.history_limit: int = config.get("history_limit", 1000)

        # Merge user overrides into defaults
        self._max_retries: Dict[ExceptionType, int] = dict(self._DEFAULT_MAX_RETRIES)
        for k, v in config.get("max_retries", {}).items():
            try:
                self._max_retries[ExceptionType(k)] = int(v)
            except (ValueError, KeyError):
                pass

        self._recovery_map: Dict[ExceptionType, RecoveryActionType] = dict(
            self._DEFAULT_RECOVERY
        )
        for k, v in config.get("recovery_overrides", {}).items():
            try:
                self._recovery_map[ExceptionType(k)] = RecoveryActionType(v)
            except (ValueError, KeyError):
                pass

        # Statistics
        self._history: List[ExceptionRecord] = []
        self._counts: Dict[ExceptionType, int] = defaultdict(int)
        self._recent_attempts: Dict[str, List[float]] = defaultdict(list)

        logger.info("ExceptionHandler initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_config(self, params: Dict[str, Any]) -> None:
        """
        Accept runtime parameter updates from the feedback loop.

        Args:
            params: Dictionary of parameter name -> new value.
                Supported keys: retry_count.
        """
        if "retry_count" in params:
            new_retry = int(params["retry_count"])
            for exc_type in self._max_retries:
                self._max_retries[exc_type] = max(
                    self._max_retries[exc_type], new_retry
                )
        logger.info("ExceptionHandler config updated: %s", params)

    def handle(self, exception: BaseException, context: Dict[str, Any]) -> RecoveryAction:
        """
        Classify an exception and determine a recovery action.

        Args:
            exception: The caught exception.
            context: Arbitrary context (e.g. task_id, arm_id, attempt,
                module_name).

        Returns:
            A ``RecoveryAction`` describing what to do next.
        """
        exc_type = self._classify_exception(exception)
        self._counts[exc_type] += 1

        logger.info(
            "Handling exception of type %s: %s", exc_type.value, str(exception)[:200]
        )

        recovery = self._determine_recovery(exc_type, context)

        # Store a provisional record (outcome filled later via
        # ``record_exception``).
        self._history.append(
            ExceptionRecord(
                timestamp=time.time(),
                exception_type=exc_type,
                message=str(exception),
                recovery=recovery,
                outcome="pending",
                context=dict(context),
            )
        )
        self._trim_history()

        return recovery

    def record_exception(
        self,
        exception: BaseException,
        recovery: RecoveryAction,
        outcome: str,
    ) -> None:
        """
        Record the outcome of a recovery attempt.

        This updates the most recent pending record that matches the
        given exception and recovery action.

        Args:
            exception: The original exception.
            recovery: The recovery action that was taken.
            outcome: One of ``"success"``, ``"failure"``, ``"partial"``.
        """
        # Walk history in reverse to find the matching pending record
        for record in reversed(self._history):
            if (
                record.outcome == "pending"
                and record.message == str(exception)
                and record.recovery.action_type == recovery.action_type
            ):
                record.outcome = outcome
                logger.debug(
                    "Recorded outcome '%s' for exception type %s",
                    outcome,
                    record.exception_type.value,
                )
                return

        # No matching pending record -- append a new one
        self._history.append(
            ExceptionRecord(
                timestamp=time.time(),
                exception_type=self._classify_exception(exception),
                message=str(exception),
                recovery=recovery,
                outcome=outcome,
            )
        )
        self._trim_history()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Return a summary of exception statistics.

        Returns:
            Dictionary with counts per type, success rates, etc.
        """
        total = len(self._history)
        by_type: Dict[str, int] = {
            k.value: v for k, v in self._counts.items()
        }
        outcomes: Dict[str, int] = defaultdict(int)
        for rec in self._history:
            outcomes[rec.outcome] += 1

        success_count = outcomes.get("success", 0)
        resolved_count = success_count + outcomes.get("partial", 0)
        success_rate = resolved_count / total if total > 0 else 0.0

        return {
            "total_exceptions": total,
            "by_type": by_type,
            "outcomes": dict(outcomes),
            "success_rate": success_rate,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_exception(self, exception: BaseException) -> ExceptionType:
        """
        Map a Python exception to an ``ExceptionType``.

        Classification is based on the exception class name and message
        content.  Subclasses can override for project-specific types.
        """
        name = type(exception).__name__.lower()
        msg = str(exception).lower()

        # --- Timeout ---
        if (
            "timeout" in name
            or "timeouterror" in name
            or "timeout" in msg
            or "timed out" in msg
        ):
            return ExceptionType.TIMEOUT

        # --- Communication ---
        if (
            "connection" in name
            or "communication" in name
            or "socket" in name
            or "broken pipe" in msg
            or "connection refused" in msg
        ):
            return ExceptionType.COMMUNICATION_FAILURE

        # --- Collision ---
        if "collision" in name or "collision" in msg:
            return ExceptionType.COLLISION

        # --- Resource conflict ---
        if (
            "resource" in name
            or "conflict" in name
            or "resource" in msg
            or "busy" in msg
            or "locked" in msg
        ):
            return ExceptionType.RESOURCE_CONFLICT

        # --- Constraint violation ---
        if (
            "constraint" in name
            or "validation" in name
            or "constraint" in msg
            or "violation" in msg
        ):
            return ExceptionType.CONSTRAINT_VIOLATION

        # --- Simulation ---
        if (
            "simulation" in name
            or "sim" in name
            or "simulation" in msg
        ):
            return ExceptionType.SIMULATION_ERROR

        # --- Code generation ---
        if (
            "syntax" in name
            or "codegen" in name
            or "generation" in msg
            or "compile" in msg
        ):
            return ExceptionType.CODE_GENERATION_ERROR

        # Fallback -- treat as simulation error (most generic)
        logger.debug(
            "Could not precisely classify exception '%s'; defaulting to SIMULATION_ERROR",
            name,
        )
        return ExceptionType.SIMULATION_ERROR

    def _determine_recovery(
        self,
        exception_type: ExceptionType,
        context: Dict[str, Any],
    ) -> RecoveryAction:
        """
        Choose a recovery action based on exception type, context, and
        recent attempt history.
        """
        task_id: str = context.get("task_id", "unknown")
        attempt: int = context.get("attempt", 1)
        max_retries = self._max_retries.get(exception_type, 2)

        # Track recent attempts for this task + exception combo
        key = f"{task_id}:{exception_type.value}"
        self._recent_attempts[key].append(time.time())

        action_type = self._recovery_map.get(
            exception_type, RecoveryActionType.RETRY
        )
        priority = self._DEFAULT_PRIORITY.get(exception_type, 50)

        # If we have exceeded retry limits, escalate to REPLAN or SKIP
        if attempt >= max_retries:
            if action_type == RecoveryActionType.RETRY:
                # Escalate
                action_type = RecoveryActionType.REPLAN
                priority += 10
                logger.info(
                    "Retry limit reached for %s; escalating to REPLAN",
                    exception_type.value,
                )

        # Build parameters
        parameters: Dict[str, Any] = {
            "exception_type": exception_type.value,
            "attempt": attempt,
            "max_retries": max_retries,
        }

        # Add type-specific parameters
        if exception_type == ExceptionType.TIMEOUT:
            # Suggest increasing timeout by 50 %
            current_timeout = context.get("timeout", 30.0)
            parameters["suggested_timeout"] = current_timeout * 1.5

        elif exception_type == ExceptionType.RESOURCE_CONFLICT:
            parameters["conflicting_resource"] = context.get("resource_id", "unknown")
            parameters["suggested_action"] = "reassign_or_wait"

        elif exception_type == ExceptionType.COLLISION:
            parameters["suggested_action"] = "replan_trajectory"
            parameters["clearance_margin"] = context.get("clearance_margin", 0.1)

        elif exception_type == ExceptionType.CODE_GENERATION_ERROR:
            parameters["suggested_action"] = "regenerate_with_constraints"
            parameters["error_context"] = context.get("error_detail", "")

        return RecoveryAction(
            action_type=action_type,
            parameters=parameters,
            priority=priority,
        )

    def _trim_history(self) -> None:
        """Keep the history list within the configured limit."""
        if len(self._history) > self.history_limit:
            overflow = len(self._history) - self.history_limit
            self._history = self._history[overflow:]
