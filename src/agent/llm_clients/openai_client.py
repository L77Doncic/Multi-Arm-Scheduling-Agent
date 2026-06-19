"""
OpenAI LLM client implementation.

Uses the ``openai`` Python SDK to interact with the OpenAI Chat Completions
API.  Supports free-form generation, structured JSON output (via response
format), retry with exponential backoff, and optional ``tiktoken``-based
token counting.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from .base import LLMClient, LLMConfig, estimate_token_count

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """LLM client backed by the OpenAI Chat Completions API.

    Parameters
    ----------
    config:
        Client configuration.  ``config.model`` defaults to ``"gpt-4o"`` if
        not set.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        if config is None:
            config = LLMConfig(model="gpt-4o")
        super().__init__(config)

        # Lazy-import so the rest of the project can load without openai.
        try:
            import openai as _openai  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIClient. "
                "Install it with: pip install openai"
            ) from exc

        self._openai = _openai

        api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "An OpenAI API key must be provided via config.api_key or "
                "the OPENAI_API_KEY environment variable."
            )

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if config.api_base:
            client_kwargs["base_url"] = config.api_base

        self._client = _openai.OpenAI(**client_kwargs)

        # Try to load tiktoken for accurate token counting.
        self._tokenizer = None
        try:
            import tiktoken

            self._tokenizer = tiktoken.encoding_for_model(config.model)
            logger.debug("tiktoken tokenizer loaded for model %s", config.model)
        except Exception:  # pragma: no cover – best effort
            logger.debug(
                "tiktoken not available for model %s; using heuristic token counting",
                config.model,
            )

    # -- Public interface ---------------------------------------------------

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a chat completion for *prompt*.

        Parameters
        ----------
        prompt:
            The user message content.
        **kwargs:
            Optional overrides: ``system_prompt``, ``temperature``,
            ``max_tokens``, ``top_p``, ``timeout``.

        Returns
        -------
        str
            The assistant's response text.
        """
        return self._chat_completion(prompt, structured=False, **kwargs)

    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate a structured JSON response conforming to *schema*.

        Uses OpenAI's ``response_format`` with ``type: "json_schema"`` when
        available, falling back to prompt-based JSON extraction.

        Parameters
        ----------
        prompt:
            The user prompt (should request JSON output).
        schema:
            A JSON Schema dict.
        **kwargs:
            Optional overrides.

        Returns
        -------
        dict
            Parsed JSON response.
        """
        # Build an enhanced prompt that includes schema instructions.
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with a single JSON object that conforms "
            f"to the following JSON Schema:\n```json\n{schema_str}\n```\n\n"
            f"Do NOT include any text outside the JSON object."
        )

        raw = self._chat_completion(
            enhanced_prompt, structured=True, schema=schema, **kwargs
        )

        return self._extract_json(raw)

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken if available, else heuristic."""
        if self._tokenizer is not None:
            return len(self._tokenizer.encode(text))
        return estimate_token_count(text)

    def get_model_name(self) -> str:
        return self._config.model

    # -- Internal -----------------------------------------------------------

    def _chat_completion(
        self,
        prompt: str,
        *,
        structured: bool = False,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Issue a chat-completion request with retry logic."""
        temperature = kwargs.get("temperature", self._config.temperature)
        max_tokens = kwargs.get("max_tokens", self._config.max_tokens)
        top_p = kwargs.get("top_p", self._config.top_p)
        timeout = kwargs.get("timeout", self._config.timeout)
        system_prompt = kwargs.get(
            "system_prompt",
            "You are a helpful assistant for multi-arm robotic scheduling.",
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        request_kwargs: Dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "timeout": timeout,
        }

        # Attempt to use structured output via response_format.
        if structured and schema is not None:
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "strict": True,
                    "schema": schema,
                },
            }

        def _call() -> str:
            logger.debug(
                "OpenAI request: model=%s, structured=%s",
                self._config.model,
                structured,
            )
            try:
                response = self._client.chat.completions.create(
                    **request_kwargs
                )
            except TypeError:
                # The SDK may not support response_format with json_schema;
                # retry without it.
                if "response_format" in request_kwargs:
                    logger.debug(
                        "response_format not supported; retrying without it"
                    )
                    fallback_kw = {
                        k: v
                        for k, v in request_kwargs.items()
                        if k != "response_format"
                    }
                    response = self._client.chat.completions.create(
                        **fallback_kw
                    )
                else:
                    raise

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI returned an empty response.")
            return content.strip()

        # Retryable errors: rate-limit (429), server errors (5xx), timeouts.
        import openai as _openai  # noqa: F811

        retryable = (
            _openai.RateLimitError,
            _openai.APITimeoutError,
            _openai.APIConnectionError,
            _openai.InternalServerError,
        )

        return self._retry(_call, retryable_exceptions=retryable)
