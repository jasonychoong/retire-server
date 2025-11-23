"""Tests for the model registry helpers."""

from __future__ import annotations

import sys
import types

import pytest

from server.agents.chat import model_registry
from server.agents.chat.model_registry import (
    MissingAPIKeyError,
    ModelClient,
    ModelProvider,
    UnknownModelError,
    create_model_client,
    get_model_config,
)


def test_get_model_config_returns_entry() -> None:
    config = get_model_config("gpt-5.1")
    assert config.model_id == "gpt-5.1"
    assert config.provider is ModelProvider.OPENAI


def test_get_model_config_unknown() -> None:
    with pytest.raises(UnknownModelError):
        get_model_config("made-up-model")


def test_create_model_client_openai_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class DummyModel:
        def __init__(self, *, client_args: dict[str, str], model_id: str) -> None:
            self.client_args = client_args
            self.model_id = model_id

    monkeypatch.setattr(model_registry, "_import_openai_model", lambda: DummyModel)

    client = create_model_client("gpt-5-mini")

    assert isinstance(client, ModelClient)
    assert client.provider is ModelProvider.OPENAI
    assert client.client.client_args == {"api_key": "test-key"}
    assert client.client.model_id == "gpt-5-mini"


@pytest.mark.parametrize("model_code", ["gemini-2.5-flash", "gemini-2.5-pro"])
def test_create_model_client_gemini_stub(monkeypatch: pytest.MonkeyPatch, model_code: str) -> None:
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "gem-key")

    google_pkg = types.ModuleType("google")
    genai_pkg = types.ModuleType("google.genai")

    class DummyGenerativeModel:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

    def configure(*, api_key: str) -> None:
        genai_pkg.configured_key = api_key

    genai_pkg.GenerativeModel = DummyGenerativeModel
    genai_pkg.configure = configure
    google_pkg.genai = genai_pkg

    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.genai", genai_pkg)

    class DummyGeminiModel:
        def __init__(self, *, client_args: dict[str, str], model_id: str) -> None:
            self.client_args = client_args
            self.model_id = model_id

    monkeypatch.setattr(model_registry, "_import_gemini_model", lambda: DummyGeminiModel)

    client = create_model_client(model_code)

    assert client.provider is ModelProvider.GEMINI
    assert client.client.model_id == model_code
    assert client.client.client_args == {"api_key": "gem-key"}


def test_create_model_client_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        create_model_client("gpt-5.1")
