"""
Synchronous LLM Client.

Provides a simple synchronous interface (generate / generate_structured)
that the TaskPlanner and CodeGenerator expect.  Wraps the OpenAI SDK
(which is used in sync mode) and works with any OpenAI-compatible API
endpoint such as ModelScope, Together, or local vLLM.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SyncLLMClient:
    """
    Synchronous LLM client with ``generate()`` and ``generate_structured()``
    methods.

    This class is designed to be passed directly to TaskPlanner and
    CodeGenerator as their ``llm_client`` parameter.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the sync LLM client.

        Args:
            config: Dictionary with keys:
                - api_key: API key (required)
                - api_base / base_url: API base URL (required)
                - model: Model name (required)
                - temperature: Sampling temperature (default 0.7)
                - max_tokens: Max output tokens (default 4096)
                - max_retries: Number of retries on failure (default 3)
                - retry_delay: Base delay between retries in seconds (default 1.0)
        """
        from openai import OpenAI

        self.api_key = config.get("api_key", "")
        self.api_base = config.get("api_base") or config.get("base_url", "")
        self.model = config.get("model", "gpt-4-turbo")
        self.temperature = float(config.get("temperature", 0.7))
        self.max_tokens = int(config.get("max_tokens", 4096))
        self.max_retries = int(config.get("max_retries", 3))
        self.retry_delay = float(config.get("retry_delay", 1.0))

        if not self.api_key:
            raise ValueError(
                "LLM API key is required. Set 'api_key' in config or the "
                "OPENAI_API_KEY environment variable."
            )
        if not self.api_base:
            raise ValueError(
                "LLM API base URL is required. Set 'api_base' in config."
            )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
        )

        logger.info(
            "SyncLLMClient initialized: model=%s, base=%s",
            self.model,
            self.api_base,
        )

    # ------------------------------------------------------------------
    # Public API — used by TaskPlanner and CodeGenerator
    # ------------------------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a text response from a prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Optional overrides for temperature, max_tokens.

        Returns:
            The generated text as a string.
        """
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert robotics and scheduling assistant. "
                    "Follow the user's instructions precisely and output "
                    "only what is requested."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        return self._call_with_retry(messages, temperature, max_tokens)

    def generate_structured(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a structured (JSON) response from a prompt.

        Args:
            prompt: The input prompt string (should ask for JSON output).
            schema: Optional JSON schema for validation (used in prompt).
            **kwargs: Optional overrides for temperature, max_tokens.

        Returns:
            Parsed JSON dictionary.
        """
        # Augment prompt with schema if provided
        full_prompt = prompt
        if schema:
            full_prompt += (
                "\n\nYour response must conform to this JSON schema:\n"
                + json.dumps(schema, indent=2, ensure_ascii=False)
            )

        full_prompt += "\n\nRespond with ONLY valid JSON, no markdown formatting."

        temperature = kwargs.get("temperature", min(self.temperature, 0.3))
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert robotics and scheduling assistant. "
                    "You must respond with valid JSON only — no markdown, "
                    "no code fences, no extra text."
                ),
            },
            {"role": "user", "content": full_prompt},
        ]

        raw = self._call_with_retry(messages, temperature, max_tokens)
        return self._extract_json(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_with_retry(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call the LLM API with retry logic."""
        import time as _time

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM")
                logger.debug(
                    "LLM call succeeded (attempt %d): %d chars",
                    attempt,
                    len(content),
                )
                return content.strip()
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    _time.sleep(self.retry_delay * attempt)

        raise RuntimeError(
            f"LLM call failed after {self.max_retries} attempts: {last_error}"
        )

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        Extract a JSON object from a text response.

        Handles responses wrapped in ```json ... ``` code fences
        and responses with leading/trailing non-JSON text.
        """
        # Try to find a JSON code block
        json_block_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
        )
        if json_block_match:
            text = json_block_match.group(1).strip()

        # Try to find a bare JSON object/array
        # Find the first { or [ and the matching last } or ]
        start_brace = text.find("{")
        start_bracket = text.find("[")

        if start_brace == -1 and start_bracket == -1:
            logger.warning("No JSON found in response: %s", text[:200])
            return {}

        if start_brace == -1:
            start = start_bracket
            end_char = "]"
        elif start_bracket == -1:
            start = start_brace
            end_char = "}"
        else:
            if start_brace < start_bracket:
                start = start_brace
                end_char = "}"
            else:
                start = start_bracket
                end_char = "]"

        end = text.rfind(end_char)
        if end == -1 or end <= start:
            logger.warning("Malformed JSON in response: %s", text[:200])
            return {}

        json_str = text[start : end + 1]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse error: %s\nText: %s", exc, json_str[:200])
            # Last resort: try to fix common issues
            try:
                # Remove trailing commas
                cleaned = re.sub(r",\s*}", "}", json_str)
                cleaned = re.sub(r",\s*]", "]", cleaned)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.error("Could not parse JSON from LLM response")
                return {}
