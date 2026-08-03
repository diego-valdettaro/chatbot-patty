"""Tests for the local LLM configuration boundary."""

import os

import pytest

from patty_bot.infrastructure.config import LLMConfigurationError, LLMSettings, load_llm_settings


def test_load_llm_settings_returns_openai_configuration_from_environment() -> None:
    settings = load_llm_settings(
        {
            "PATTY_LLM_PROVIDER": "openai",
            "PATTY_LLM_MODEL": "test-model",
            "OPENAI_API_KEY": "test-key",
            "LANGSMITH_API_KEY": "langsmith-test-key",
        }
    )

    assert settings == LLMSettings(
        provider="openai",
        model="test-model",
        api_key="test-key",
        langsmith_api_key="langsmith-test-key",
    )


def test_load_llm_settings_defaults_to_openai_provider() -> None:
    settings = load_llm_settings(
        {
            "PATTY_LLM_MODEL": "test-model",
            "OPENAI_API_KEY": "test-key",
            "LANGSMITH_API_KEY": "langsmith-test-key",
        }
    )

    assert settings.provider == "openai"
    assert settings.reasoning_effort == "low"


def test_load_llm_settings_allows_an_explicit_reasoning_effort() -> None:
    settings = load_llm_settings(
        {
            "PATTY_LLM_MODEL": "gpt-5.6-terra",
            "PATTY_LLM_REASONING_EFFORT": "medium",
            "OPENAI_API_KEY": "test-key",
            "LANGSMITH_API_KEY": "langsmith-test-key",
        }
    )

    assert settings.reasoning_effort == "medium"


def test_load_llm_settings_loads_dotenv_only_when_no_mapping_is_supplied(monkeypatch) -> None:
    loaded_paths = []
    monkeypatch.setattr("patty_bot.infrastructure.config.load_dotenv", lambda path, override: loaded_paths.append((path, override)))
    monkeypatch.setenv("PATTY_LLM_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_API_KEY", "langsmith-test-key")

    settings = load_llm_settings()

    assert settings.model == "test-model"
    assert loaded_paths and loaded_paths[0][1] is False
    assert settings.langsmith_project == "patty-chatbot"
    assert os.environ["LANGSMITH_TRACING"] == "true"


@pytest.mark.parametrize(
    ("environment", "message"),
    (
        ({"PATTY_LLM_MODEL": "test-model"}, "OPENAI_API_KEY"),
        ({"OPENAI_API_KEY": "test-key"}, "PATTY_LLM_MODEL"),
        (
            {"PATTY_LLM_MODEL": "test-model", "OPENAI_API_KEY": "test-key"},
            "LANGSMITH_API_KEY",
        ),
        (
            {
                "PATTY_LLM_PROVIDER": "other",
                "PATTY_LLM_MODEL": "test-model",
                "OPENAI_API_KEY": "test-key",
                "LANGSMITH_API_KEY": "langsmith-test-key",
            },
            "Unsupported LLM provider",
        ),
        (
            {
                "PATTY_LLM_MODEL": "test-model",
                "PATTY_LLM_REASONING_EFFORT": "fast",
                "OPENAI_API_KEY": "test-key",
                "LANGSMITH_API_KEY": "langsmith-test-key",
            },
            "Unsupported reasoning effort",
        ),
    ),
)
def test_load_llm_settings_rejects_incomplete_or_unsupported_configuration(
    environment: dict[str, str], message: str
) -> None:
    with pytest.raises(LLMConfigurationError, match=message):
        load_llm_settings(environment)
