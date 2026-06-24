"""
LLM Clients Module

This module provides unified interfaces for various LLM providers.
"""

from .base import BaseLLMClient, LLMMessage, LLMResponse
from .openai_client import OpenAIClient

# Anthropic client is optional (requires anthropic package)
try:
    from .anthropic_client import AnthropicClient
except ImportError:
    AnthropicClient = None

__all__ = [
    "BaseLLMClient",
    "LLMResponse",
    "LLMMessage",
    "OpenAIClient",
    "AnthropicClient",
]
