"""Safe, non-identifying metadata for third-party observability services."""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from patty_bot.agent.tool_contracts import ToolResult


def redacted_text_metadata(value: str) -> dict[str, int | bool]:
    """Describe text without retaining any of its potentially identifying content."""

    return {"redacted": True, "character_count": len(value)}


def safe_turn_inputs(
    *,
    user_message: str,
    conversation: Sequence[Mapping[str, str]],
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    """Return the only conversation metadata allowed in an external trace."""

    role_counts = Counter(
        role
        for message in conversation
        if (role := message.get("role")) in {"user", "assistant"}
    )
    return {
        "model": model,
        "reasoning_effort": reasoning_effort,
        "user_message": redacted_text_metadata(user_message),
        "conversation": {
            "message_count": sum(role_counts.values()),
            "role_counts": dict(sorted(role_counts.items())),
        },
    }


def safe_turn_outputs(*, reply: str, cart_item_count: int, order_confirmed: bool) -> dict[str, Any]:
    """Return response metrics without retaining an assistant reply that may echo PII."""

    return {
        "reply": redacted_text_metadata(reply),
        "cart_item_count": cart_item_count,
        "order_confirmed": order_confirmed,
    }


def safe_tool_inputs(*, name: str, arguments: Mapping[str, object]) -> dict[str, Any]:
    """Record tool identity and shape only; argument values never leave the process."""

    return {"name": name, "argument_count": len(arguments)}


def safe_tool_outputs(result: ToolResult) -> dict[str, Any]:
    """Record outcome codes only; tool data can contain order details and must stay local."""

    return {
        "ok": result.ok,
        "error_codes": [error.code for error in result.errors],
    }
