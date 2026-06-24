"""
Anthropic LLM Client Implementation

This module implements the Anthropic API client for Claude models.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic

from .base import BaseLLMClient, LLMMessage, LLMResponse, MessageRole

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """
    Anthropic API client implementation.

    Supports Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku, and other Claude models.
    """

    # Pricing per 1K tokens (as of 2024)
    PRICING = {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-2.1": {"input": 0.008, "output": 0.024},
        "claude-2.0": {"input": 0.008, "output": 0.024},
        "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Anthropic client.

        Args:
            config: Configuration dictionary with keys:
                - api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
                - model: Model name (default: 'claude-3-sonnet-20240229')
                - base_url: Optional custom API base URL
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens (default: 4096)
        """
        super().__init__(config)

        # Get API key from config or environment
        api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key must be provided in config or ANTHROPIC_API_KEY environment variable"
            )

        # Initialize client
        base_url = config.get("base_url")
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)

        # Set model
        self.model = config.get("model", "claude-3-sonnet-20240229")

        logger.info(f"Anthropic client initialized with model: {self.model}")

    def _convert_messages(
        self, messages: List[LLMMessage]
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Convert messages to Anthropic format.

        Anthropic requires:
        - System message as a separate parameter
        - Messages alternating between user and assistant

        Args:
            messages: List of LLMMessage objects.

        Returns:
            Tuple of (system_prompt, messages_list).
        """
        system_prompt = None
        converted_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                converted_messages.append(
                    {"role": msg.role.value, "content": msg.content}
                )

        # Ensure messages alternate correctly
        # Anthropic requires messages to start with user
        if converted_messages and converted_messages[0]["role"] != "user":
            converted_messages.insert(
                0, {"role": "user", "content": "Please proceed with the task."}
            )

        return system_prompt, converted_messages

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Send a chat request to Anthropic.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (overrides default).
            max_tokens: Maximum tokens to generate (overrides default).
            **kwargs: Additional parameters:
                - top_p: Nucleus sampling parameter
                - top_k: Top-k sampling parameter
                - stop_sequences: Stop sequences

        Returns:
            LLMResponse object containing the response.
        """
        # Validate messages
        if not self.validate_messages(messages):
            raise ValueError("Invalid messages format")

        # Convert messages to Anthropic format
        system_prompt, converted_messages = self._convert_messages(messages)

        # Prepare parameters
        params = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        # Add system prompt if present
        if system_prompt:
            params["system"] = system_prompt

        # Add optional parameters
        if "top_p" in kwargs:
            params["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            params["top_k"] = kwargs["top_k"]
        if "stop_sequences" in kwargs:
            params["stop_sequences"] = kwargs["stop_sequences"]

        try:
            logger.debug(f"Sending chat request with {len(messages)} messages")

            # Make API call
            response = await self.client.messages.create(**params)

            # Extract response
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            }

            # Calculate cost
            cost = self._calculate_cost(usage)
            self._total_cost += cost

            # Create response object
            llm_response = LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason,
                metadata={"cost": cost},
            )

            # Update usage statistics
            self._update_usage(llm_response)

            logger.debug(
                f"Chat response received: {usage['total_tokens']} tokens, "
                f"${cost:.4f} cost"
            )

            return llm_response

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    async def complete(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Send a completion request to Anthropic.

        Note: This converts the prompt to a chat message for compatibility.

        Args:
            prompt: The prompt text.
            temperature: Sampling temperature (overrides default).
            max_tokens: Maximum tokens to generate (overrides default).
            **kwargs: Additional parameters.

        Returns:
            LLMResponse object containing the response.
        """
        # Convert to chat format
        messages = [self.create_user_message(prompt)]
        return await self.chat(messages, temperature, max_tokens, **kwargs)

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """
        Calculate the cost of an API call.

        Args:
            usage: Dictionary with token usage information.

        Returns:
            Cost in USD.
        """
        pricing = self.PRICING.get(
            self.model, self.PRICING.get("claude-3-sonnet-20240229")
        )

        input_cost = (usage["prompt_tokens"] / 1000) * pricing["input"]
        output_cost = (usage["completion_tokens"] / 1000) * pricing["output"]

        return input_cost + output_cost

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary containing model information.
        """
        return {
            "provider": "anthropic",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "total_cost": self._total_cost,
            "total_tokens": self._total_tokens,
        }

    async def stream_chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        """
        Stream a chat response from Anthropic.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters.

        Yields:
            Chunks of the response text.
        """
        # Validate messages
        if not self.validate_messages(messages):
            raise ValueError("Invalid messages format")

        # Convert messages to Anthropic format
        system_prompt, converted_messages = self._convert_messages(messages)

        # Prepare parameters
        params = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        # Add system prompt if present
        if system_prompt:
            params["system"] = system_prompt

        try:
            logger.debug(f"Starting stream chat with {len(messages)} messages")

            # Make streaming API call
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {str(e)}")
            raise
