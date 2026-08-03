"""Acceptance scenarios for chat-driven order changes using a fake LLM provider."""

import json
from datetime import date
from pathlib import Path

import pytest

from patty_bot.agent.router import run_agent_turn
from patty_bot.domain.catalog import load_catalog
from patty_bot.infrastructure.config import LLMSettings
from patty_bot.agent.tool_executor import AgentSession, execute_tool_call
from patty_bot.agent.tool_contracts import ToolCall


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
REFERENCE_DATE = date(2026, 7, 25)


@pytest.fixture(autouse=True)
def disable_live_langsmith_tracing(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


def session() -> AgentSession:
    return AgentSession(
        products=load_catalog(Path("data/catalog.sample.csv")),
        database_path=Path("data/test-order.sqlite3"),
        reference_date=REFERENCE_DATE,
    )


def tool_call(name: str, arguments: dict, call_id: str) -> dict:
    return {
        "output": [
            {
                "type": "function_call",
                "name": name,
                "arguments": json.dumps(arguments),
                "call_id": call_id,
            }
        ],
        "output_text": "",
    }


def test_chat_can_build_a_complete_pickup_order_and_get_its_summary() -> None:
    client = FakeClient(
        [
            tool_call("search_catalog", {"query": "red velvet"}, "search"),
            tool_call("add_to_cart", {"product_id": "cake-red-velvet-mediana"}, "add"),
            tool_call(
                "update_order_details",
                {
                    "customer_name": "Diego",
                    "customer_phone": "999888777",
                    "fulfillment_type": "pickup",
                    "requested_date": "2026-07-27",
                    "delivery_address": None,
                    "pickup_store": "Benavides",
                },
                "details",
            ),
            tool_call("get_order_summary", {}, "summary"),
            {"output": [], "output_text": "Tu pedido para recojo está listo para revisar."},
        ]
    )

    turn = run_agent_turn(client, SETTINGS, session(), "Quiero una red velvet para recoger en Benavides")

    assert turn.reply == "Tu pedido para recojo está listo para revisar."
    assert turn.session.cart.items[0].product.id == "cake-red-velvet-mediana"
    assert turn.session.order_details.customer_name == "Diego"
    assert turn.session.order_details.fulfillment_type == "pickup"
    assert turn.session.order_details.pickup_store == "Benavides"
    summary_output = json.loads(client.responses.requests[-1]["input"][-1]["output"])
    assert summary_output["data"]["delivery_fee"] == "0.00"
    assert summary_output["data"]["total"] == "82.00"
    assert summary_output["data"]["validation"]["is_valid"] is True


def test_chat_can_apply_a_quantity_change_using_the_previous_conversation() -> None:
    initial = execute_tool_call(
        session(), ToolCall(name="add_to_cart", arguments={"product_id": "brownie-chocolate-belga"})
    ).session
    client = FakeClient(
        [
            tool_call(
                "change_cart_quantity",
                {"product_id": "brownie-chocolate-belga", "quantity": 3},
                "quantity",
            ),
            {"output": [], "output_text": "Listo, ahora tienes tres brownies."},
        ]
    )
    conversation = [
        {"role": "user", "content": "Quiero un brownie."},
        {"role": "assistant", "content": "Agregué un brownie a tu carrito."},
    ]

    turn = run_agent_turn(client, SETTINGS, initial, "Agrega dos más", conversation)

    assert turn.session.cart.items[0].quantity == 3
    # The router appends tool replay items to this list after the request; the new user turn stays at index 2.
    assert client.responses.requests[0]["input"][2] == {"role": "user", "content": "Agrega dos más"}


def test_chat_handles_an_unavailable_product_without_changing_the_order() -> None:
    client = FakeClient(
        [
                tool_call("search_catalog", {"query": "paneton"}, "search"),
            {"output": [], "output_text": "No la tenemos disponible; puedo mostrarte alternativas."},
        ]
    )

    turn = run_agent_turn(client, SETTINGS, session(), "Quiero un paneton")

    assert turn.session.cart.is_empty
    search_output = json.loads(client.responses.requests[1]["input"][-1]["output"])
    assert search_output["ok"] is True
    assert search_output["data"]["matches"] == []
