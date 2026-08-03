"""Tests for the JSON-serializable contract shared by all agent tools."""

import pytest

from patty_bot.agent.tool_contracts import ToolCall, ToolError, ToolResult, tool_failure, tool_success


def test_tool_call_serializes_name_and_json_arguments() -> None:
    call = ToolCall(name="search_catalog", arguments={"query": "hamburguesa", "limit": 2})

    assert call.to_dict() == {
        "name": "search_catalog",
        "arguments": {"query": "hamburguesa", "limit": 2},
    }


def test_tool_call_rejects_non_json_arguments() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        ToolCall(name="search_catalog", arguments={"query": {"not", "json"}})

    with pytest.raises(ValueError, match="JSON object"):
        ToolCall(name="search_catalog", arguments=["not", "an", "object"])  # type: ignore[arg-type]


def test_successful_tool_result_serializes_data_without_errors() -> None:
    result = tool_success({"products": [{"id": "classic", "price": "18.00"}]})

    assert result.to_dict() == {
        "ok": True,
        "data": {"products": [{"id": "classic", "price": "18.00"}]},
        "errors": [],
    }


def test_failed_tool_result_serializes_controlled_error() -> None:
    result = tool_failure(
        ToolError(
            code="invalid_argument",
            message="Quantity must be greater than zero.",
            field="quantity",
        )
    )

    assert result.to_dict() == {
        "ok": False,
        "data": {},
        "errors": [
            {
                "code": "invalid_argument",
                "message": "Quantity must be greater than zero.",
                "field": "quantity",
            }
        ],
    }


def test_result_requires_errors_when_not_ok() -> None:
    with pytest.raises(ValueError, match="must contain at least one error"):
        ToolResult(ok=False)


def test_successful_result_rejects_errors() -> None:
    error = ToolError(code="invalid_argument", message="Invalid argument.")

    with pytest.raises(ValueError, match="cannot contain errors"):
        ToolResult(ok=True, errors=(error,))


def test_result_rejects_non_json_data() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        tool_success({"subtotal": object()})
