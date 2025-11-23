"""Model registry and provider helpers for the chat agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ModelProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GEMINI = "gemini"


@dataclass(frozen=True)
class ModelConfig:
    """Metadata describing how to talk to a provider/model."""

    code: str
    provider: ModelProvider
    model_id: str
    description: str
    supports_streaming: bool = True


@dataclass
class ModelClient:
    """Runtime client wrapper for a configured model."""

    provider: ModelProvider
    model_id: str
    client: object


class ModelRegistryError(RuntimeError):
    """Base error for registry issues."""


class UnknownModelError(ModelRegistryError):
    """Raised when a model code is not defined."""


class MissingDependencyError(ModelRegistryError):
    """Raised when a required SDK is unavailable."""


class MissingAPIKeyError(ModelRegistryError):
    """Raised when no API key is configured for a provider."""


MODEL_REGISTRY: Dict[str, ModelConfig] = {
    "gpt-5.1-mini": ModelConfig(
        code="gpt-5.1-mini",
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.1-mini",
        description="Cost-effective GPT-5.1 variant suitable for experimentation.",
    ),
    "gpt-5.1": ModelConfig(
        code="gpt-5.1",
        provider=ModelProvider.OPENAI,
        model_id="gpt-5.1",
        description="Full GPT-5.1 model for higher-quality outputs.",
    ),
    "gemini-2.5": ModelConfig(
        code="gemini-2.5",
        provider=ModelProvider.GEMINI,
        model_id="gemini-2.5",
        description="Latest high-quality Gemini model.",
    ),
    "gemini-2.5-flash": ModelConfig(
        code="gemini-2.5-flash",
        provider=ModelProvider.GEMINI,
        model_id="gemini-2.5-flash",
        description="Flash variant optimized for speed/latency tradeoffs.",
    ),
}


def get_model_config(model_code: str) -> ModelConfig:
    """Return the config for a model code."""

    try:
        return MODEL_REGISTRY[model_code]
    except KeyError as exc:
        raise UnknownModelError(f"Unknown model code: {model_code}") from exc


def create_model_client(model_code: str) -> ModelClient:
    """Instantiate a provider client for the given model."""

    config = get_model_config(model_code)
    if config.provider is ModelProvider.OPENAI:
        client = _build_openai_client(config)
    elif config.provider is ModelProvider.GEMINI:
        client = _build_gemini_client(config)
    else:  # pragma: no cover - defensive
        raise UnknownModelError(f"Unsupported provider: {config.provider}")
    return ModelClient(provider=config.provider, model_id=config.model_id, client=client)


def _build_openai_client(config: ModelConfig) -> object:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("OPENAI_API_KEY is not set.")
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise MissingDependencyError("Install openai>=1.42.0 to use GPT models.") from exc
    return OpenAI(api_key=api_key)


def _build_gemini_client(config: ModelConfig) -> object:
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("GOOGLE_AI_API_KEY is not set.")
    try:
        import google.genai as genai
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise MissingDependencyError("Install google-genai>=1.52.0 to use Gemini models.") from exc
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name=config.model_id)

