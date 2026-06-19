"""
Prompt Templates for Multi-Arm Scheduling Agent.

Contains reusable prompt functions for task decomposition, resource
allocation, and code generation workflows.
"""

from .task_decomposition import (
    task_decompose_prompt,
    dependency_analysis_prompt,
)
from .resource_allocation import (
    resource_allocate_prompt,
    conflict_resolve_prompt,
)
from .code_generation import (
    code_generate_prompt,
    code_refine_prompt,
)

__all__ = [
    "task_decompose_prompt",
    "dependency_analysis_prompt",
    "resource_allocate_prompt",
    "conflict_resolve_prompt",
    "code_generate_prompt",
    "code_refine_prompt",
]
