"""Tests for the provider-facing agent loop using a simulated Responses client."""

import json
from datetime import date
from pathlib import Path

import pytest

from patty_bot.agent.router import (
    MAX_CONVERSATION_MESSAGES,
    MAX_TOOL_ROUNDS,
    SYSTEM_INSTRUCTIONS,
    run_agent_turn,
)
from patty_bot.domain.catalog import load_catalog
from patty_bot.infrastructure.config import LLMSettings
from patty_bot.agent.tool_executor import AgentSession


class FakeResponses:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self._responses)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


SETTINGS = LLMSettings(
    provider="openai",
    model="test-model",
    api_key="test-key",
    langsmith_api_key="langsmith-test-key",
)


@pytest.fixture(autouse=True)
def disable_live_langsmith_tracing(monkeypatch) -> None:
    """Unit tests exercise local trace structure without posting runs to LangSmith."""

    monkeypatch.setenv("LANGSMITH_TRACING", "false")


def session() -> AgentSession:
    return AgentSession(
        products=load_catalog(Path("data/catalog.sample.csv")),
        database_path=Path("data/test-order.sqlite3"),
        reference_date=date(2026, 7, 25),
    )


def test_router_executes_a_tool_and_returns_the_follow_up_reply() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "add_to_cart",
                        "arguments": json.dumps({"product_id": "brownie-chocolate-belga"}),
                        "call_id": "call_1",
                    }
                ],
                "output_text": "",
            },
            {"output": [], "output_text": "Listo, agregue el brownie a tu carrito."},
        ]
    )

    turn = run_agent_turn(client, SETTINGS, session(), "Quiero un brownie")

    assert turn.reply == "Listo, agregue el brownie a tu carrito."
    assert turn.session.cart.items[0].product.id == "brownie-chocolate-belga"
    assert client.responses.requests[0]["instructions"] == SYSTEM_INSTRUCTIONS
    assert client.responses.requests[0]["parallel_tool_calls"] is False
    assert client.responses.requests[0]["reasoning"] == {"effort": "low"}
    replayed_input = client.responses.requests[1]["input"]
    assert replayed_input[-1]["type"] == "function_call_output"
    assert json.loads(replayed_input[-1]["output"])["ok"] is True


def test_instructions_distinguish_catalog_search_from_recommendations() -> None:
    assert "search_catalog cuando el cliente sabe" in SYSTEM_INSTRUCTIONS
    assert "recommend_products cuando describe necesidades" in SYSTEM_INSTRUCTIONS


def test_router_never_allows_the_model_to_confirm_an_order() -> None:
    client = FakeClient(
        [
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "confirm_order",
                        "arguments": "{}",
                        "call_id": "call_1",
                    }
                ],
                "output_text": "",
            },
            {"output": [], "output_text": "Confirma el pedido usando el boton de la interfaz."},
        ]
    )

    turn = run_agent_turn(client, SETTINGS, session(), "Confirmalo")

    assert turn.session.confirmed_order is None
    replayed_output = client.responses.requests[1]["input"][-1]["output"]
    assert json.loads(replayed_output)["errors"][0]["code"] == "confirmation_required"


def test_router_sends_recent_conversation_before_the_new_user_message() -> None:
    client = FakeClient([{"output": [], "output_text": "La agregare al carrito."}])
    conversation = [
        {"role": "user", "content": "Quiero una torta de chocolate grande."},
        {"role": "assistant", "content": "Encontre una torta de chocolate. La agrego?"},
    ]

    run_agent_turn(client, SETTINGS, session(), "Si", conversation)

    assert client.responses.requests[0]["input"] == [
        *conversation,
        {"role": "user", "content": "Si"},
    ]


def test_router_limits_and_filters_conversation_history() -> None:
    client = FakeClient([{"output": [], "output_text": "Listo."}])
    conversation = [
        {"role": "user", "content": str(index)} for index in range(MAX_CONVERSATION_MESSAGES + 3)
    ] + [{"role": "tool", "content": "private"}, {"role": "assistant", "content": ""}]

    run_agent_turn(client, SETTINGS, session(), "continuar", conversation)

    input_items = client.responses.requests[0]["input"]
    assert len(input_items) == MAX_CONVERSATION_MESSAGES + 1
    assert input_items[0] == {"role": "user", "content": "3"}
    assert input_items[-1] == {"role": "user", "content": "continuar"}


def test_router_stops_after_a_bounded_number_of_tool_rounds() -> None:
    function_response = {
        "output": [
            {"type": "function_call", "name": "get_cart", "arguments": "{}", "call_id": "call"}
        ],
        "output_text": "",
    }
    client = FakeClient([function_response] * MAX_TOOL_ROUNDS)

    turn = run_agent_turn(client, SETTINGS, session(), "Que tengo?")

    assert len(client.responses.requests) == MAX_TOOL_ROUNDS
    assert turn.reply == "No pude completar el pedido en este momento. Intenta nuevamente."
