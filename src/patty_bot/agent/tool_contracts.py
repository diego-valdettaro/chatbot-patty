from dataclasses import dataclass, field
from typing import Mapping, TypeAlias


# Tool payloads must remain portable across the UI, the future LLM provider, and test fixtures.
JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class ToolCall:
    """A structured request that an agent can send to a domain tool."""

    name: str
    arguments: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Reject malformed calls at the boundary instead of allowing tool implementations to guess.
        if not self.name.strip():
            raise ValueError("Tool name cannot be empty.")
        if not _is_json_object(self.arguments):
            raise ValueError("Tool arguments must be a JSON object.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "arguments": dict(self.arguments)}


@dataclass(frozen=True)
class ToolError:
    """A controlled domain error returned by a tool."""

    code: str
    message: str
    field: str | None = None

    def __post_init__(self) -> None:
        # Error codes support programmatic recovery; messages remain safe to expose to the agent.
        if not self.code.strip():
            raise ValueError("Tool error code cannot be empty.")
        if not self.message.strip():
            raise ValueError("Tool error message cannot be empty.")
        if self.field is not None and not self.field.strip():
            raise ValueError("Tool error field cannot be empty when provided.")

    def to_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.field is not None:
            payload["field"] = self.field
        return payload


@dataclass(frozen=True)
class ToolResult:
    """The serializable success or failure response of a domain tool."""

    ok: bool
    data: Mapping[str, JsonValue] = field(default_factory=dict)
    errors: tuple[ToolError, ...] = ()

    def __post_init__(self) -> None:
        # A result has exactly one outcome, which keeps callers from handling mixed success/error states.
        if not _is_json_object(self.data):
            raise ValueError("Tool result data must be a JSON object.")
        if self.ok and self.errors:
            raise ValueError("Successful tool results cannot contain errors.")
        if not self.ok and not self.errors:
            raise ValueError("Failed tool results must contain at least one error.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "ok": self.ok,
            "data": dict(self.data),
            "errors": [error.to_dict() for error in self.errors],
        }


def tool_success(data: Mapping[str, JsonValue] | None = None) -> ToolResult:
    return ToolResult(ok=True, data=data or {})


def tool_failure(*errors: ToolError) -> ToolResult:
    return ToolResult(ok=False, errors=errors)


def _is_json_object(value: object) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(key, str) and _is_json_value(item) for key, item in value.items()
    )


def _is_json_value(value: object) -> bool:
    # Validate recursively because nested payloads are serialized after the tool returns.
    if value is None or isinstance(value, bool | int | float | str):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return _is_json_object(value)
    return False
