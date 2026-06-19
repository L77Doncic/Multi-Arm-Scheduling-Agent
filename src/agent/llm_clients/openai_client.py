"""
OpenAI LLM Client Implementation

This module implements the OpenAI API client for GPT models.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI

from .base import BaseLLMClient, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client implementation.

    Supports GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and other OpenAI models.
    """

    # Pricing per 1K tokens (as of 2024)
    PRICING = {
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-32k': {'input': 0.06, 'output': 0.12},
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'gpt-3.5-turbo-16k': {'input': 0.003, 'output': 0.004},
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI client.

        Args:
            config: Configuration dictionary with keys:
                - api_key: OpenAI API key (or set OPENAI_API_KEY env var)
                - model: Model name (default: 'gpt-4-turbo')
                - base_url: Optional custom API base URL
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens (default: 4096)
        """
        super().__init__(config)

        # Get API key from config or environment
        api_key = config.get('api_key') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OpenAI API key must be provided in config or OPENAI_API_KEY environment variable"
            )

        # Initialize client
        base_url = config.get('base_url')
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # Set model
        self.model = config.get('model', 'gpt-4-turbo')

        logger.info(f"OpenAI client initialized with model: {self.model}")

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat request to OpenAI.

        Args:
            messages: List of messages in the conversation.
            temperature: Sampling temperature (overrides default).
            max_tokens: Maximum tokens to generate (overrides default).
            **kwargs: Additional parameters:
                - top_p: Nucleus sampling parameter
                - frequency_penalty: Frequency penalty
                - presence_penalty: Presence penalty
                - stop: Stop sequences

        Returns:
            LLMResponse object containing the response.
        """
        # Validate messages
        if not self.validate_messages(messages):
            raise ValueError("Invalid messages format")

        # Prepare parameters
        params = {
            'model': self.model,
            'messages': [msg.to_dict() for msg in messages],
            'temperature': temperature or self.temperature,
            'max_tokens': max_tokens or self.max_tokens,
            'top_p': kwargs.get('top_p', self.top_p),
        }

        # Add optional parameters
        if 'frequency_penalty' in kwargs:
            params['frequency_penalty'] = kwargs['frequency_penalty']
        if 'presence_penalty' in kwargs:
            params['presence_penalty'] = kwargs['presence_penalty']
        if 'stop' in kwargs:
            params['stop'] = kwargs['stop']

        try:
            logger.debug(f"Sending chat request with {len(messages)} messages")

            # Make API call
            response = await self.client.chat.completions.create(**params)

            # Extract response
            choice = response.choices[0]
            usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
            }

            # Calculate cost
            cost = self._calculate_cost(usage)
            self._total_cost += cost

            # Create response object
            llm_response = LLMResponse(
                content=choice.message.content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                metadata={'cost': cost}
            )

            # Update usage statistics
            self._update_usage(llm_response)

            logger.debug(
                f"Chat response received: {usage['total_tokens']} tokens, "
                f"${cost:.4f} cost"
            )

            return llm_response

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def complete(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send a completion request to OpenAI.

        Note: This converts the prompt to a chat message for compatibility.
        OpenAI's completion API is deprecated for newer models.

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
        pricing = self.PRICING.get(self.model, self.PRICING.get('gpt-4-turbo'))

        input_cost = (usage['prompt_tokens'] / 1000) * pricing['input']
        output_cost = (usage['completion_tokens'] / 1000) * pricing['output']

        return input_cost + output_cost

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary containing model information.
        """
        return {
            'provider': 'openai',
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'total_cost': self._total_cost,
            'total_tokens': self._total_tokens,
        }

    async def stream_chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Stream a chat response from OpenAI.

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

        # Prepare parameters
        params = {
            'model': self.model,
            'messages': [msg.to_dict() for msg in messages],
            'temperature': temperature or self.temperature,
            'max_tokens': max_tokens or self.max_tokens,
            'top_p': kwargs.get('top_p', self.top_p),
            'stream': True,
        }

        try:
            logger.debug(f"Starting stream chat with {len(messages)} messages")

            # Make streaming API call
            stream = await self.client.chat.completions.create(**params)

            # Yield chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            raise
