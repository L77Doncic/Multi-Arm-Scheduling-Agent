"""
Abstract base class and configuration for LLM clients.

This module defines the ``LLMClient`` ABC that all provider-specific clients
must implement, as well as the ``LLMConfig`` dataclass used to configure them.
Shared utilities for retry logic with exponential backoff and token counting
are included here.
"""

from __future__ import annotations

import abc
import json
import logging
import math
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    """Configuration for an LLM client instance.

    Attributes:
        model: Model identifier (e.g. ``"gpt-4o"``, ``"claude-sonnet-4-20250514"``).
        temperature: Sampling temperature in [0, 2].
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling parameter in [0, 1].
        api_key: API key for the provider.  If ``None`` the client will fall
            back to the relevant environment variable.
        api_base: Override the default API base URL.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts on transient failures.
        retry_delay: Base delay (seconds) for exponential backoff.
    """

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError(
                f"temperature must be in [0, 2], got {self.temperature}"
            )
        if self.max_tokens < 1:
            raise ValueError(
                f"max_tokens must be >= 1, got {self.max_tokens}"
            )
        if self.top_p < 0 or self.top_p > 1:
            raise ValueError(f"top_p must be in [0, 1], got {self.top_p}")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be > 0, got {self.timeout}")
        if self.max_retries < 0:
            raise ValueError(
                f"max_retries must be >= 0, got {self.max_retries}"
            )
        if self.retry_delay < 0:
            raise ValueError(
                f"retry_delay must be >= 0, got {self.retry_delay}"
            )


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _retry_with_backoff(
    fn,
    *,
    max_retries: int,
    retry_delay: float,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Any:
    """Call *fn* with exponential backoff.

    Parameters
    ----------
    fn:
        A zero-argument callable to execute.
    max_retries:
        Maximum number of retries (0 means no retries).
    retry_delay:
        Base delay in seconds; actual delay = ``retry_delay * 2 ** attempt``.
    retryable_exceptions:
        Exception types that trigger a retry.  All others propagate
        immediately.

    Returns
    -------
    Any
        The return value of *fn*.

    Raises
    ------
    Exception
        The last exception raised by *fn* if all retries are exhausted.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    "All %d retries exhausted. Last error: %s",
                    max_retries,
                    exc,
                )
                raise
            delay = retry_delay * (2 ** attempt)
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %.1fs ...",
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError("Unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Token counting utility
# ---------------------------------------------------------------------------

# Average characters per token for English text.  This is a rough heuristic;
# provider-specific clients can override ``count_tokens`` with a more accurate
# implementation (e.g. using tiktoken).
_AVG_CHARS_PER_TOKEN = 4.0


def estimate_token_count(text: str) -> int:
    """Estimate the number of tokens in *text* using a character heuristic.

    This is intentionally simple; for production accuracy, use a proper
    tokenizer such as ``tiktoken`` (OpenAI) or the Anthropic token-counting
    API.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / _AVG_CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class LLMClient(abc.ABC):
    """Abstract base class that every LLM provider client must implement.

    Subclasses must override at least:
    * ``generate``
    * ``generate_structured``
    * ``get_model_name``

    ``count_tokens`` has a default heuristic implementation that subclasses
    are encouraged to replace with a provider-specific tokenizer.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        logger.info(
            "LLMClient initialized with model=%s, max_retries=%d",
            config.model,
            config.max_retries,
        )

    # -- Public interface ---------------------------------------------------

    @abc.abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a free-form text completion for *prompt*.

        Parameters
        ----------
        prompt:
            The user prompt.
        **kwargs:
            Provider-specific overrides (e.g. ``temperature``).

        Returns
        -------
        str
            The model's response text.
        """

    @abc.abstractmethod
    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate a structured (JSON) response that conforms to *schema*.

        Parameters
        ----------
        prompt:
            The user prompt (should instruct the model to return JSON).
        schema:
            A JSON Schema dict describing the expected output shape.
        **kwargs:
            Provider-specific overrides.

        Returns
        -------
        dict
            Parsed JSON response.
        """

    def count_tokens(self, text: str) -> int:
        """Return the number of tokens in *text*.

        The default implementation uses a simple character heuristic.
        Subclasses should override this with a provider-specific tokenizer
        when available.
        """
        return estimate_token_count(text)

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier string."""

    # -- Helpers ------------------------------------------------------------

    @property
    def config(self) -> LLMConfig:
        """Access the current configuration (read-only)."""
        return self._config

    def _retry(
        self,
        fn,
        *,
        retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    ) -> Any:
        """Convenience wrapper around :func:`_retry_with_backoff` using the
        client's own retry settings."""
        return _retry_with_backoff(
            fn,
            max_retries=self._config.max_retries,
            retry_delay=self._config.retry_delay,
            retryable_exceptions=retryable_exceptions,
        )

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Best-effort extraction of a JSON object from *text*.

        Handles cases where the model wraps the JSON in markdown fences or
        includes leading/trailing commentary.
        """
        # Try direct parse first.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON block in markdown fences.
        fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
        match = fence_pattern.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find the first { ... } or [ ... ] block.
        for open_char, close_char in [("{", "}"), ("[", "]")]:
            start = text.find(open_char)
            if start == -1:
                continue
            depth = 0
            for idx in range(start, len(text)):
                if text[idx] == open_char:
                    depth += 1
                elif text[idx] == close_char:
                    depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : idx + 1])
                    except json.JSONDecodeError:
                        break

        raise ValueError(
            "Could not extract valid JSON from model response. "
            f"Response text (first 500 chars): {text[:500]!r}"
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self._config.model!r})"
