"""Tests for the redacted boundary used by external traces."""

from patty_bot.agent.tool_contracts import ToolError, tool_failure, tool_success
from patty_bot.infrastructure.observability import (
    safe_tool_inputs,
    safe_tool_outputs,
    safe_turn_inputs,
    safe_turn_outputs,
)


def test_turn_metadata_never_contains_message_or_conversation_content() -> None:
    secret = "Ana Perez, +34 600 123 456, Calle Mayor 10"

    metadata = safe_turn_inputs(
        user_message=secret,
        conversation=[{"role": "user", "content": secret}, {"role": "assistant", "content": secret}],
        model="test-model",
        reasoning_effort="low",
    )

    assert metadata["user_message"] == {"redacted": True, "character_count": len(secret)}
    assert metadata["conversation"] == {"message_count": 2, "role_counts": {"assistant": 1, "user": 1}}
    assert secret not in repr(metadata)


def test_tool_metadata_never_contains_raw_arguments_or_result_data() -> None:
    secret = "Ana Perez, +34 600 123 456, Calle Mayor 10"
    inputs = safe_tool_inputs(name="update_order_details", arguments={"customer_name": secret})
    success = safe_tool_outputs(tool_success({"order_details": {"customer_name": secret}}))
    failure = safe_tool_outputs(tool_failure(ToolError(code="invalid_argument", message=secret)))

    assert inputs == {"name": "update_order_details", "argument_count": 1}
    assert success == {"ok": True, "error_codes": []}
    assert failure == {"ok": False, "error_codes": ["invalid_argument"]}
    assert secret not in repr((inputs, success, failure))


def test_turn_output_never_contains_reply_that_may_echo_customer_data() -> None:
    secret = "Ana Perez, +34 600 123 456, Calle Mayor 10"

    metadata = safe_turn_outputs(reply=secret, cart_item_count=2, order_confirmed=False)

    assert metadata == {
        "reply": {"redacted": True, "character_count": len(secret)},
        "cart_item_count": 2,
        "order_confirmed": False,
    }
    assert secret not in repr(metadata)
