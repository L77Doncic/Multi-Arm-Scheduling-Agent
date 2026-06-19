"""
Factory module for creating LLM client instances.

Usage::

    from agent.llm_clients import create_llm_client

    client = create_llm_client({
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.5,
    })
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .base import LLMClient, LLMConfig

logger = logging.getLogger(__name__)

# Registry of provider name -> client class.
# Lazy-loaded so that optional dependencies (openai, anthropic) are only
# imported when actually needed.
_PROVIDER_REGISTRY: Dict[str, str] = {
    "openai": "agent.llm_clients.openai_client.OpenAIClient",
    "anthropic": "agent.llm_clients.anthropic_client.AnthropicClient",
}


def _resolve_class(dotted_path: str) -> type[LLMClient]:
    """Import and return the class at *dotted_path*."""
    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path:
        raise ImportError(f"Invalid class path: {dotted_path!r}")

    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, LLMClient)):
        raise TypeError(
            f"{dotted_path!r} does not resolve to an LLMClient subclass."
        )
    return cls


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """Create and return an :class:`LLMClient` instance from *config*.

    Parameters
    ----------
    config:
        A dictionary with the following keys (all optional except
        ``provider``):

        * ``provider`` (str, **required**): ``"openai"`` or ``"anthropic"``.
        * ``model`` (str): Model identifier.
        * ``temperature`` (float): Sampling temperature.
        * ``max_tokens`` (int): Maximum output tokens.
        * ``top_p`` (float): Nucleus sampling.
        * ``api_key`` (str): API key.
        * ``api_base`` (str): API base URL.
        * ``timeout`` (float): Request timeout in seconds.
        * ``max_retries`` (int): Retry count.
        * ``retry_delay`` (float): Base retry delay in seconds.

    Returns
    -------
    LLMClient
        A concrete client instance.

    Raises
    ------
    ValueError
        If ``provider`` is missing or unknown.
    """
    config = dict(config)  # shallow copy to avoid mutating the caller's dict

    provider = config.pop("provider", None)
    if provider is None:
        raise ValueError(
            "config must include a 'provider' key "
            f"(one of {list(_PROVIDER_REGISTRY)})."
        )

    provider = provider.lower()
    if provider not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown provider {provider!r}. "
            f"Supported providers: {list(_PROVIDER_REGISTRY)}."
        )

    # Build LLMConfig from remaining keys (ignore unknown keys gracefully).
    llm_config = LLMConfig(
        **{k: v for k, v in config.items() if k in LLMConfig.__dataclass_fields__}
    )

    class_path = _PROVIDER_REGISTRY[provider]
    logger.info("Creating LLM client: provider=%s, model=%s", provider, llm_config.model)

    client_cls = _resolve_class(class_path)
    return client_cls(config=llm_config)
