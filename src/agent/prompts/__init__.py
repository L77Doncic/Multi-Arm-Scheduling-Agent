"""
Prompts Module

This module provides prompt templates for various LLM tasks.
"""

from .task_decomposition import TaskDecompositionPrompts
from .resource_allocation import ResourceAllocationPrompts
from .code_generation import CodeGenerationPrompts

__all__ = [
    'TaskDecompositionPrompts',
    'ResourceAllocationPrompts',
    'CodeGenerationPrompts',
]
