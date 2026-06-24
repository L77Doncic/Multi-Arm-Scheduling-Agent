"""
Prompts Module

This module provides prompt templates for various LLM tasks.
"""

from .code_generation import CodeGenerationPrompts
from .resource_allocation import ResourceAllocationPrompts
from .task_decomposition import TaskDecompositionPrompts

__all__ = [
    "TaskDecompositionPrompts",
    "ResourceAllocationPrompts",
    "CodeGenerationPrompts",
]
