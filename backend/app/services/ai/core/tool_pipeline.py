from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ValidationError

from app.schemas.tool_result import ToolResult, ToolResultStatus, to_dict


TOOL_CALLER_ASSISTANT = "assistant_chat"
TOOL_CALLER_WORKFLOW_AGENT = "workflow_agent_chat"
TOOL_CALLER_WORKFLOW_NODE = "workflow_node_agent"


@dataclass(frozen=True)
class ToolIdentity:
    name: str
    description: str
    namespace: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolPolicy:
    allowed_callers: frozenset[str]
    risk_level: str = "low"
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ToolExecutionContext:
    caller: str
    allowed_tool_names: frozenset[str] | None = None


@dataclass(frozen=True)
class ToolDefinition:
    identity: ToolIdentity
    args_model: type[BaseModel] | None
    args_schema: Dict[str, Any]
    executor: Callable[[Dict[str, Any]], Any]
    policy: ToolPolicy
    source: str = "native"
    legacy_tool: BaseTool | None = None


def _schema_to_dict(schema: type[BaseModel] | Dict[str, Any] | None) -> Dict[str, Any]:
    if schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(schema, dict):
        return dict(schema)
    return schema.model_json_schema()


def _status_from_payload(payload: Dict[str, Any]) -> str:
    status = str(payload.get("status") or "").strip()
    valid = {item.value for item in ToolResultStatus}
    if status in valid:
        return status
    if payload.get("confirmation_id") or payload.get("action"):
        return ToolResultStatus.CONFIRMATION_REQUIRED.value
    if payload.get("success") is False:
        return ToolResultStatus.FAILED.value
    return ToolResultStatus.SUCCESS.value


def _message_from_payload(payload: Dict[str, Any], success: bool) -> str:
    message = str(payload.get("message") or "").strip()
    if message:
        return message
    return "工具执行成功" if success else "工具执行失败"


def _wrap_scalar_result(result: Any) -> Dict[str, Any]:
    if result is None:
        return {"success": True, "data": None}
    if isinstance(result, str):
        return {"success": True, "message": result, "data": {"text": result}}
    return {"success": True, "data": result}


def normalize_tool_result(
    result: Any,
    *,
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if isinstance(result, ToolResult):
        payload = to_dict(result)
    elif isinstance(result, BaseModel):
        payload = result.model_dump(exclude_none=True, mode="json")
    elif isinstance(result, dict):
        payload = dict(result)
    else:
        payload = _wrap_scalar_result(result)

    success = bool(payload.get("success", True))
    payload["success"] = success
    payload["status"] = _status_from_payload(payload)
    payload["message"] = _message_from_payload(payload, success)
    payload.setdefault("tool_name", tool_name)
    if args is not None:
        payload.setdefault("args", args)
    return payload


def build_tool_error_result(
    *,
    tool_name: str,
    error: str,
    args: Optional[Dict[str, Any]] = None,
    code: str = "tool_error",
    validation_errors: Optional[list[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": False,
        "status": ToolResultStatus.FAILED.value,
        "message": error,
        "error": error,
        "error_code": code,
        "tool_name": tool_name,
    }
    if args is not None:
        payload["args"] = args
    if validation_errors:
        payload["validation_errors"] = validation_errors
    return payload


def build_tool_start_event(
    *,
    tool_name: str,
    args: Dict[str, Any],
    tool: BaseTool | None = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    policy = dict((tool.metadata or {}).get("tool_policy") or {}) if tool else {}
    return {
        "type": "tool_start",
        "data": {
            "tool_name": tool_name,
            "args": args,
            "call_id": call_id,
            "status": "running",
            "policy": policy,
        },
    }


def build_tool_end_event(
    *,
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
    tool: BaseTool | None = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized = normalize_tool_result(result, tool_name=tool_name, args=args)
    policy = dict((tool.metadata or {}).get("tool_policy") or {}) if tool else {}
    return {
        "type": "tool_end",
        "data": {
            "tool_name": tool_name,
            "args": args,
            "call_id": call_id,
            "status": normalized.get("status"),
            "policy": policy,
            "result": normalized,
            "success": normalized.get("success"),
        },
    }


def _validation_error_items(exc: ValidationError) -> list[Dict[str, Any]]:
    items: list[Dict[str, Any]] = []
    for item in exc.errors():
        items.append(
            {
                "loc": [str(part) for part in item.get("loc", ())],
                "msg": str(item.get("msg") or "invalid"),
                "type": str(item.get("type") or "validation_error"),
            }
        )
    return items


def _format_validation_message(errors: list[Dict[str, Any]]) -> str:
    segments: list[str] = []
    for item in errors[:5]:
        loc = ".".join(item.get("loc") or []) or "(root)"
        segments.append(f"{loc}: {item.get('msg')}")
    details = "；".join(segments)
    return f"工具参数校验失败：{details}" if details else "工具参数校验失败"


def _validate_args(definition: ToolDefinition, args: Dict[str, Any]) -> Dict[str, Any]:
    if definition.args_model is None:
        return dict(args)
    validated = definition.args_model.model_validate(args)
    return validated.model_dump(exclude_none=False, mode="json")


def _is_allowed(definition: ToolDefinition, context: ToolExecutionContext) -> bool:
    if context.caller not in definition.policy.allowed_callers:
        return False
    if context.allowed_tool_names is None:
        return True
    return definition.identity.name in context.allowed_tool_names


def _tool_metadata(definition: ToolDefinition) -> Dict[str, Any]:
    return {
        "tool_policy": {
            "allowed_callers": sorted(definition.policy.allowed_callers),
            "risk_level": definition.policy.risk_level,
            "requires_confirmation": definition.policy.requires_confirmation,
            "namespace": definition.identity.namespace,
            "source": definition.source,
        }
    }


def _make_tool_runner(
    definition: ToolDefinition,
    context: ToolExecutionContext,
) -> Callable[..., Dict[str, Any]]:
    def _runner(**kwargs: Any) -> Dict[str, Any]:
        args = dict(kwargs)
        if not _is_allowed(definition, context):
            return build_tool_error_result(
                tool_name=definition.identity.name,
                args=args,
                error=f"调用上下文 '{context.caller}' 无权使用工具 '{definition.identity.name}'",
                code="tool_forbidden",
            )
        try:
            validated_args = _validate_args(definition, args)
        except ValidationError as exc:
            errors = _validation_error_items(exc)
            return build_tool_error_result(
                tool_name=definition.identity.name,
                args=args,
                error=_format_validation_message(errors),
                code="tool_validation_error",
                validation_errors=errors,
            )

        try:
            result = definition.executor(validated_args)
        except Exception as exc:
            return build_tool_error_result(
                tool_name=definition.identity.name,
                args=validated_args,
                error=f"工具执行失败: {exc}",
            )

        return normalize_tool_result(
            result,
            tool_name=definition.identity.name,
            args=validated_args,
        )

    return _runner


def _build_wrapped_tool(
    definition: ToolDefinition,
    context: ToolExecutionContext,
) -> BaseTool:
    runner = _make_tool_runner(definition, context)
    return StructuredTool.from_function(
        func=runner,
        name=definition.identity.name,
        description=definition.identity.description,
        args_schema=definition.args_schema,
        infer_schema=False,
        metadata=_tool_metadata(definition),
        handle_tool_error=lambda exc: json.dumps(
            build_tool_error_result(
                tool_name=definition.identity.name,
                error=f"工具执行失败: {exc}",
                code="tool_error",
            ),
            ensure_ascii=False,
        ),
    )


def create_legacy_tool_definition(
    *,
    tool: BaseTool,
    namespace: str,
    allowed_callers: Iterable[str],
    risk_level: str = "low",
    requires_confirmation: bool = False,
    tags: Iterable[str] | None = None,
) -> ToolDefinition:
    schema = getattr(tool, "tool_call_schema", None) or getattr(tool, "args_schema", None)
    args_model = schema if isinstance(schema, type) and issubclass(schema, BaseModel) else None
    args_schema = _schema_to_dict(schema)
    identity = ToolIdentity(
        name=tool.name,
        description=tool.description,
        namespace=namespace,
        tags=tuple(tags or ()),
    )
    policy = ToolPolicy(
        allowed_callers=frozenset(allowed_callers),
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
    )
    return ToolDefinition(
        identity=identity,
        args_model=args_model,
        args_schema=args_schema,
        executor=lambda args: tool.invoke(args),
        policy=policy,
        source="legacy",
        legacy_tool=tool,
    )


@dataclass
class ToolRegistry:
    definitions: Dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, definition: ToolDefinition) -> ToolDefinition:
        self.definitions[definition.identity.name] = definition
        return definition

    def register_legacy_tool(self, **kwargs: Any) -> ToolDefinition:
        return self.register(create_legacy_tool_definition(**kwargs))

    def get_definition(self, name: str) -> ToolDefinition | None:
        return self.definitions.get(name)

    def list_definitions(self, namespace: Optional[str] = None) -> list[ToolDefinition]:
        items = list(self.definitions.values())
        if namespace is None:
            return items
        return [item for item in items if item.identity.namespace == namespace]

    def get_tools(
        self,
        *,
        context: ToolExecutionContext,
        namespace: Optional[str] = None,
    ) -> list[BaseTool]:
        return [
            _build_wrapped_tool(item, context)
            for item in self.list_definitions(namespace)
            if _is_allowed(item, context)
        ]

    def get_tool_map(
        self,
        *,
        context: ToolExecutionContext,
        namespace: Optional[str] = None,
    ) -> Dict[str, BaseTool]:
        tools = self.get_tools(context=context, namespace=namespace)
        return {tool.name: tool for tool in tools}

    def get_tool_descriptions(
        self,
        *,
        context: ToolExecutionContext,
        namespace: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        items = self.get_tools(context=context, namespace=namespace)
        return {
            item.name: {
                "description": item.description,
                "args": item.args,
                "policy": (item.metadata or {}).get("tool_policy") or {},
            }
            for item in items
        }

    def invoke(
        self,
        *,
        context: ToolExecutionContext,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        definition = self.get_definition(tool_name)
        if definition is None:
            return build_tool_error_result(
                tool_name=tool_name,
                args=args,
                error=f"未知工具: {tool_name}",
                code="tool_not_found",
            )
        tool = _build_wrapped_tool(definition, context)
        return tool.invoke(args or {})


AI_TOOL_REGISTRY = ToolRegistry()
