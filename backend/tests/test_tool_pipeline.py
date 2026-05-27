from __future__ import annotations

from typing import Any, Dict

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.schemas.tool_result import ToolResultStatus
from app.services.ai.core.tool_pipeline import (
    ToolDefinition,
    ToolExecutionContext,
    ToolIdentity,
    ToolPolicy,
    ToolRegistry,
    normalize_tool_result,
)


class EchoArgs(BaseModel):
    text: str = Field(min_length=1)


def _definition() -> ToolDefinition:
    return ToolDefinition(
        identity=ToolIdentity(
            name="echo_text",
            description="Echo validated text.",
            namespace="test",
        ),
        args_model=EchoArgs,
        args_schema=EchoArgs.model_json_schema(),
        executor=lambda args: {"success": True, "echo": args["text"]},
        policy=ToolPolicy(allowed_callers=frozenset({"allowed"})),
    )


def test_registry_invokes_allowed_tool_with_valid_args() -> None:
    registry = ToolRegistry()
    registry.register(_definition())

    result = registry.invoke(
        context=ToolExecutionContext(caller="allowed"),
        tool_name="echo_text",
        args={"text": "ok"},
    )

    assert result["success"] is True
    assert result["status"] == ToolResultStatus.SUCCESS.value
    assert result["echo"] == "ok"
    assert result["tool_name"] == "echo_text"


def test_registry_blocks_unauthorized_tool() -> None:
    registry = ToolRegistry()
    registry.register(_definition())

    result = registry.invoke(
        context=ToolExecutionContext(caller="blocked"),
        tool_name="echo_text",
        args={"text": "ok"},
    )

    assert result["success"] is False
    assert result["error_code"] == "tool_forbidden"


def test_registry_returns_validation_error_before_execution() -> None:
    registry = ToolRegistry()
    registry.register(_definition())

    result = registry.invoke(
        context=ToolExecutionContext(caller="allowed"),
        tool_name="echo_text",
        args={"text": ""},
    )

    assert result["success"] is False
    assert result["error_code"] == "tool_validation_error"
    assert result["validation_errors"]


def test_normalize_tool_result_preserves_confirmation_status() -> None:
    result = normalize_tool_result(
        {
            "success": False,
            "confirmation_id": "confirm-1",
            "action": "delete_card",
        },
        tool_name="delete_card",
        args={"card_id": 1},
    )

    assert result["status"] == ToolResultStatus.CONFIRMATION_REQUIRED.value
    assert result["message"] == "工具执行失败"


def test_legacy_tool_registration_invokes_wrapped_tool() -> None:
    @tool
    def double_value(value: int) -> Dict[str, Any]:
        """Double a number."""
        return {"success": True, "value": value * 2}

    registry = ToolRegistry()
    registry.register_legacy_tool(
        tool=double_value,
        namespace="legacy",
        allowed_callers=("allowed",),
    )

    result = registry.invoke(
        context=ToolExecutionContext(caller="allowed"),
        tool_name="double_value",
        args={"value": 2},
    )

    assert result["success"] is True
    assert result["value"] == 4


def test_registry_lists_allowed_tool_metadata() -> None:
    registry = ToolRegistry()
    registry.register(_definition())

    metadata = registry.list_tool_metadata(
        context=ToolExecutionContext(caller="allowed"),
        namespace="test",
    )

    assert metadata == [
        {
            "name": "echo_text",
            "description": "Echo validated text.",
            "namespace": "test",
            "args_schema": EchoArgs.model_json_schema(),
            "risk_level": "low",
            "requires_confirmation": False,
            "source": "native",
            "tags": [],
        }
    ]
