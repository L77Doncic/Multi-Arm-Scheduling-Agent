"""
Base LLM Client Abstract Class

This module defines the abstract interface for all LLM clients.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(Enum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """Represents a message in the conversation."""

    role: MessageRole
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMResponse:
    """Represents a response from the LLM."""

    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get("total_tokens", 0)

    @property
    def prompt_tokens(self) -> int:
        """Get prompt tokens used."""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """Get completion tokens used."""
        return self.usage.get("completion_tokens", 0)


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    All LLM client implementations should inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM client.

        Args:
            config: Configuration dictionary containing API keys,
                   model settings, and other parameters.
        """
        self.config = config
        self.model = config.get("model", "default")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)
        self.top_p = config.get("top_p", 0.9)
        self._total_cost = 0.0
        self._total_tokens = 0

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (overrides default).
            max_tokens: Maximum tokens to generate (overrides default).
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse object containing the response.
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send a completion request to the LLM.

        Args:
            prompt: The prompt text.
            temperature: Sampling temperature (overrides default).
            max_tokens: Maximum tokens to generate (overrides default).
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse object containing the response.
        """
        pass

    def create_message(self, role: MessageRole, content: str) -> LLMMessage:
        """
        Create a new message.

        Args:
            role: The message role (system, user, or assistant).
            content: The message content.

        Returns:
            LLMMessage object.
        """
        return LLMMessage(role=role, content=content)

    def create_system_message(self, content: str) -> LLMMessage:
        """Create a system message."""
        return self.create_message(MessageRole.SYSTEM, content)

    def create_user_message(self, content: str) -> LLMMessage:
        """Create a user message."""
        return self.create_message(MessageRole.USER, content)

    def create_assistant_message(self, content: str) -> LLMMessage:
        """Create an assistant message."""
        return self.create_message(MessageRole.ASSISTANT, content)

    @property
    def total_cost(self) -> float:
        """Get total cost of API calls."""
        return self._total_cost

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens

    def _update_usage(self, response: LLMResponse):
        """
        Update usage statistics.

        Args:
            response: The LLM response to extract usage from.
        """
        self._total_tokens += response.total_tokens

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary containing model information.
        """
        pass

    def validate_messages(self, messages: List[LLMMessage]) -> bool:
        """
        Validate message format.

        Args:
            messages: List of messages to validate.

        Returns:
            True if messages are valid, False otherwise.
        """
        if not messages:
            return False

        for msg in messages:
            if not isinstance(msg, LLMMessage):
                return False
            if not msg.content:
                return False

        return True

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated number of tokens.
        """
        # Simple estimation: ~4 characters per token
        # More accurate estimation would use tiktoken or similar
        return len(text) // 4
