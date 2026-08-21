import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


APP_TITLE = "Chatbot de pedidos Patty"

# The default delivery fee is used only until an order's fulfillment mode determines its final fee.
DELIVERY_FEE = 10

PICKUP_STORES = ("Benavides", "San Isidro")

# Resolve data paths from the repository instead of the process working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "data" / "catalogo_b2c_completo_utf8.csv"
# The sample remains available for legacy unit tests and local fixtures.
CATALOG_SAMPLE_PATH = PROJECT_ROOT / "data" / "catalog.sample.csv"
DATABASE_PATH = PROJECT_ROOT / "data" / "patty.sqlite3"
DOTENV_PATH = PROJECT_ROOT / ".env"


LLM_PROVIDER_ENV_VAR = "PATTY_LLM_PROVIDER"
LLM_MODEL_ENV_VAR = "PATTY_LLM_MODEL"
LLM_REASONING_EFFORT_ENV_VAR = "PATTY_LLM_REASONING_EFFORT"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
LANGSMITH_API_KEY_ENV_VAR = "LANGSMITH_API_KEY"
LANGSMITH_PROJECT_ENV_VAR = "LANGSMITH_PROJECT"
LANGSMITH_DEFAULT_PROJECT = "patty-chatbot"
SUPPORTED_LLM_PROVIDERS = ("openai",)
SUPPORTED_REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")


class LLMConfigurationError(ValueError):
    """Raised when the local LLM configuration cannot safely create a client."""


@dataclass(frozen=True)
class LLMSettings:
    """Provider settings loaded only when the agent integration needs them."""

    provider: str
    model: str
    api_key: str
    reasoning_effort: str = "low"
    langsmith_api_key: str = ""
    langsmith_project: str = LANGSMITH_DEFAULT_PROJECT


def load_llm_settings(environ: Mapping[str, str] | None = None) -> LLMSettings:
    """Load validated LLM settings without creating a provider client or making a network call."""
    if environ is None:
        # Local secrets stay outside version control; explicitly supplied test mappings are untouched.
        load_dotenv(DOTENV_PATH, override=False)
    environment = os.environ if environ is None else environ
    provider = environment.get(LLM_PROVIDER_ENV_VAR, "openai").strip().lower()
    model = environment.get(LLM_MODEL_ENV_VAR, "").strip()
    api_key = environment.get(OPENAI_API_KEY_ENV_VAR, "").strip()
    reasoning_effort = environment.get(LLM_REASONING_EFFORT_ENV_VAR, "low").strip().lower()
    langsmith_api_key = environment.get(LANGSMITH_API_KEY_ENV_VAR, "").strip()
    langsmith_project = environment.get(LANGSMITH_PROJECT_ENV_VAR, LANGSMITH_DEFAULT_PROJECT).strip()

    if provider not in SUPPORTED_LLM_PROVIDERS:
        supported = ", ".join(SUPPORTED_LLM_PROVIDERS)
        raise LLMConfigurationError(
            f"Unsupported LLM provider {provider!r}. Supported providers: {supported}."
        )
    if not model:
        raise LLMConfigurationError(f"{LLM_MODEL_ENV_VAR} must be configured.")
    if not api_key:
        raise LLMConfigurationError(f"{OPENAI_API_KEY_ENV_VAR} must be configured.")
    if not langsmith_api_key:
        raise LLMConfigurationError(f"{LANGSMITH_API_KEY_ENV_VAR} must be configured.")
    if not langsmith_project:
        raise LLMConfigurationError(f"{LANGSMITH_PROJECT_ENV_VAR} cannot be empty.")
    if reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
        supported = ", ".join(SUPPORTED_REASONING_EFFORTS)
        raise LLMConfigurationError(
            f"Unsupported reasoning effort {reasoning_effort!r}. Supported values: {supported}."
        )

    settings = LLMSettings(
        provider=provider,
        model=model,
        api_key=api_key,
        reasoning_effort=reasoning_effort,
        langsmith_api_key=langsmith_api_key,
        langsmith_project=langsmith_project,
    )
    if environ is None:
        # Tracing is mandatory for the live chat and is configured only after validation succeeds.
        os.environ[LANGSMITH_API_KEY_ENV_VAR] = settings.langsmith_api_key
        os.environ[LANGSMITH_PROJECT_ENV_VAR] = settings.langsmith_project
        os.environ["LANGSMITH_TRACING"] = "true"
    return settings
