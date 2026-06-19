"""
Anthropic LLM client implementation.

Uses the ``anthropic`` Python SDK to interact with the Anthropic Messages API.
Supports free-form generation, structured JSON output, retry with exponential
backoff, and heuristic-based token counting.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from .base import LLMClient, LLMConfig, estimate_token_count

logger = logging.getLogger(__name__)

# Anthropic has a hard limit per request; keep a safety margin.
_MAX_OUTPUT_TOKENS = 8192


class AnthropicClient(LLMClient):
    """LLM client backed by the Anthropic Messages API.

    Parameters
    ----------
    config:
        Client configuration.  ``config.model`` defaults to
        ``"claude-sonnet-4-20250514"`` if not set.
    """

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        if config is None:
            config = LLMConfig(model="claude-sonnet-4-20250514")
        super().__init__(config)

        try:
            import anthropic as _anthropic  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicClient. "
                "Install it with: pip install anthropic"
            ) from exc

        self._anthropic = _anthropic

        api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "An Anthropic API key must be provided via config.api_key or "
                "the ANTHROPIC_API_KEY environment variable."
            )

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if config.api_base:
            client_kwargs["base_url"] = config.api_base

        self._client = _anthropic.Anthropic(**client_kwargs)

    # -- Public interface ---------------------------------------------------

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response for *prompt* using the Messages API.

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
        return self._messages_request(prompt, structured=False, **kwargs)

    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate a structured JSON response conforming to *schema*.

        The schema is injected into the system prompt so the model knows
        exactly what JSON shape to produce.

        Parameters
        ----------
        prompt:
            The user prompt.
        schema:
            A JSON Schema dict describing the expected output shape.
        **kwargs:
            Optional overrides.

        Returns
        -------
        dict
            Parsed JSON response.
        """
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"You MUST respond with a single JSON object that conforms "
            f"to the following JSON Schema:\n```json\n{schema_str}\n```\n\n"
            f"Do NOT include any commentary, explanation, or markdown "
            f"fences outside the JSON object itself."
        )

        raw = self._messages_request(enhanced_prompt, structured=True, **kwargs)

        return self._extract_json(raw)

    def count_tokens(self, text: str) -> int:
        """Estimate token count.

        Anthropic does not ship a standalone tokenizer; this uses the shared
        character-based heuristic.
        """
        return estimate_token_count(text)

    def get_model_name(self) -> str:
        return self._config.model

    # -- Internal -----------------------------------------------------------

    def _messages_request(
        self,
        prompt: str,
        *,
        structured: bool = False,
        **kwargs: Any,
    ) -> str:
        """Issue a Messages API request with retry logic."""
        temperature = kwargs.get("temperature", self._config.temperature)
        max_tokens = min(
            kwargs.get("max_tokens", self._config.max_tokens),
            _MAX_OUTPUT_TOKENS,
        )
        top_p = kwargs.get("top_p", self._config.top_p)
        timeout = kwargs.get("timeout", self._config.timeout)
        system_prompt = kwargs.get(
            "system_prompt",
            "You are a helpful assistant for multi-arm robotic scheduling.",
        )

        if structured:
            system_prompt = (
                f"{system_prompt}\n\n"
                "You MUST always respond with valid JSON only. "
                "Do not include any text outside the JSON object."
            )

        def _call() -> str:
            logger.debug(
                "Anthropic request: model=%s, structured=%s",
                self._config.model,
                structured,
            )
            response = self._client.messages.create(
                model=self._config.model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout,
            )

            # The response content is a list of blocks; concatenate text blocks.
            text_parts = [
                block.text
                for block in response.content
                if block.type == "text"
            ]
            if not text_parts:
                raise ValueError(
                    "Anthropic returned no text content in the response."
                )
            return "".join(text_parts).strip()

        # Retryable errors: rate-limit, overloaded, API errors, timeouts.
        import anthropic as _anthropic  # noqa: F811

        retryable = (
            _anthropic.RateLimitError,
            _anthropic.OverloadedError,
            _anthropic.APITimeoutError,
            _anthropic.APIConnectionError,
            _anthropic.InternalServerError,
        )

        return self._retry(_call, retryable_exceptions=retryable)
