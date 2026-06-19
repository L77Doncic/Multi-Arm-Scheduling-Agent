"""
Unit tests for LLM clients module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from agent.llm_clients.base import BaseLLMClient, LLMMessage, LLMResponse, MessageRole
from agent.llm_clients.openai_client import OpenAIClient
from agent.llm_clients.anthropic_client import AnthropicClient


class TestLLMMessage:
    """Test LLMMessage class."""

    def test_create_message(self):
        """Test creating a message."""
        msg = LLMMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_to_dict(self):
        """Test converting message to dictionary."""
        msg = LLMMessage(role=MessageRole.SYSTEM, content="System prompt")
        result = msg.to_dict()
        assert result == {"role": "system", "content": "System prompt"}

    def test_message_roles(self):
        """Test all message roles."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"


class TestLLMResponse:
    """Test LLMResponse class."""

    def test_create_response(self):
        """Test creating a response."""
        response = LLMResponse(
            content="Hello!",
            model="gpt-4",
            usage={'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}
        )
        assert response.content == "Hello!"
        assert response.model == "gpt-4"
        assert response.total_tokens == 15
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 5

    def test_default_usage(self):
        """Test response with default usage."""
        response = LLMResponse(content="test", model="gpt-4")
        assert response.total_tokens == 0
        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0


class TestOpenAIClient:
    """Test OpenAI client."""

    def test_client_initialization(self):
        """Test client initialization with config."""
        config = {
            'api_key': 'test-key',
            'model': 'gpt-4-turbo',
            'temperature': 0.5
        }
        client = OpenAIClient(config)
        assert client.model == 'gpt-4-turbo'
        assert client.temperature == 0.5

    def test_client_initialization_no_key(self):
        """Test client initialization without API key raises error."""
        config = {'model': 'gpt-4'}
        with pytest.raises(ValueError, match="OpenAI API key must be provided"):
            OpenAIClient(config)

    def test_get_model_info(self):
        """Test getting model info."""
        config = {'api_key': 'test-key', 'model': 'gpt-4'}
        client = OpenAIClient(config)
        info = client.get_model_info()
        assert info['provider'] == 'openai'
        assert info['model'] == 'gpt-4'

    def test_estimate_tokens(self):
        """Test token estimation."""
        config = {'api_key': 'test-key'}
        client = OpenAIClient(config)
        tokens = client.estimate_tokens("Hello world, this is a test.")
        assert tokens > 0


class TestAnthropicClient:
    """Test Anthropic client."""

    def test_client_initialization(self):
        """Test client initialization with config."""
        config = {
            'api_key': 'test-key',
            'model': 'claude-3-sonnet-20240229',
            'temperature': 0.7
        }
        client = AnthropicClient(config)
        assert client.model == 'claude-3-sonnet-20240229'
        assert client.temperature == 0.7

    def test_client_initialization_no_key(self):
        """Test client initialization without API key raises error."""
        config = {'model': 'claude-3-sonnet'}
        with pytest.raises(ValueError, match="Anthropic API key must be provided"):
            AnthropicClient(config)

    def test_get_model_info(self):
        """Test getting model info."""
        config = {'api_key': 'test-key', 'model': 'claude-3-sonnet-20240229'}
        client = AnthropicClient(config)
        info = client.get_model_info()
        assert info['provider'] == 'anthropic'
        assert info['model'] == 'claude-3-sonnet-20240229'

    def test_convert_messages(self):
        """Test message conversion for Anthropic format."""
        config = {'api_key': 'test-key'}
        client = AnthropicClient(config)

        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="System prompt"),
            LLMMessage(role=MessageRole.USER, content="User message"),
            LLMMessage(role=MessageRole.ASSISTANT, content="Assistant response"),
            LLMMessage(role=MessageRole.USER, content="Follow up"),
        ]

        system_prompt, converted = client._convert_messages(messages)

        assert system_prompt == "System prompt"
        assert len(converted) == 3
        assert converted[0]['role'] == 'user'
        assert converted[1]['role'] == 'assistant'
        assert converted[2]['role'] == 'user'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
