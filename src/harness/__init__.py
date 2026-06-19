"""
Harness Engineering Framework

This package provides the core harness modules for multi-arm scheduling:
decomposition, allocation, validation, exception handling, and feedback.
"""

from .task_decomposer import TaskDecomposer, DecomposedTask

from .resource_allocator import (
    ResourceAllocator,
    Conflict,
    ConflictType,
    TaskInfo,
    ArmInfo,
)

from .result_validator import (
    ResultValidator,
    ValidationResult,
    Constraint,
    ConstraintType,
    Severity,
    Violation,
)

from .exception_handler import (
    ExceptionHandler,
    ExceptionType,
    RecoveryAction,
    RecoveryActionType,
    ExceptionRecord,
)

from .feedback_loop import (
    FeedbackLoop,
    FeedbackData,
    AnalysisResult,
    StrategyAdjustment,
    StrategyParameter,
)

__all__ = [
    # task_decomposer
    "TaskDecomposer",
    "DecomposedTask",
    # resource_allocator
    "ResourceAllocator",
    "Conflict",
    "ConflictType",
    "TaskInfo",
    "ArmInfo",
    # result_validator
    "ResultValidator",
    "ValidationResult",
    "Constraint",
    "ConstraintType",
    "Severity",
    "Violation",
    # exception_handler
    "ExceptionHandler",
    "ExceptionType",
    "RecoveryAction",
    "RecoveryActionType",
    "ExceptionRecord",
    # feedback_loop
    "FeedbackLoop",
    "FeedbackData",
    "AnalysisResult",
    "StrategyAdjustment",
    "StrategyParameter",
]
