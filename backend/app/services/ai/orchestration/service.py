from __future__ import annotations

from typing import Any, AsyncGenerator

from loguru import logger
from sqlmodel import Session

from app.schemas.agent_orchestration import AgentResult, AgentRoleConfig, AgentTask
from app.schemas.ai import AssistantChatRequest
from app.services.ai.assistant.tools import AssistantDeps, get_assistant_tools, set_assistant_deps
from app.services.ai.core.tool_agent_stream import stream_agent_with_tools

from .registry import DEFAULT_AGENT_REGISTRY, WRITING_AGENT_ID, AgentRegistry


class AgentOrchestrationError(RuntimeError):
    pass


class AgentToolAuthorizationError(AgentOrchestrationError):
    pass


def build_delegated_task(
    *,
    task_type: str,
    target_agent_id: str,
    content: str,
    route_key: str | None = None,
    requested_tool_names: list[str] | None = None,
    context: dict[str, Any] | None = None,
) -> AgentTask:
    return AgentTask(
        task_type=task_type,
        target_agent_id=target_agent_id,
        content=content,
        route_key=route_key,
        requested_tool_names=requested_tool_names or [],
        context=context or {},
    )


def build_success_result(task: AgentTask, content: str, payload: dict[str, Any] | None = None) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        source_agent_id=task.target_agent_id,
        status="succeeded",
        content=content,
        payload=payload or {},
    )


def build_failed_result(task: AgentTask, error: str, payload: dict[str, Any] | None = None) -> AgentResult:
    return AgentResult(
        task_id=task.task_id,
        source_agent_id=task.target_agent_id,
        status="failed",
        error=error,
        payload=payload or {},
    )


def ensure_allowed_tool_scope(role: AgentRoleConfig, requested_tool_names: list[str]) -> None:
    allowed = set(role.allowed_tool_names)
    blocked = sorted({name for name in requested_tool_names if name not in allowed})
    if blocked:
        raise AgentToolAuthorizationError(
            f"agent '{role.agent_id}' 未授权工具: {', '.join(blocked)}"
        )


def _assistant_task_type(request: AssistantChatRequest) -> str:
    explicit = (getattr(request, "agent_task_type", None) or "").strip()
    if explicit:
        return explicit
    return "writing"


def _assistant_user_prompt(request: AssistantChatRequest) -> str:
    parts: list[str] = []
    if request.context_info:
        parts.append(request.context_info)
    if request.user_prompt:
        parts.append("\nUser: " + request.user_prompt)
    return "\n\n".join(parts) if parts else "(User input is empty; assistant should clarify intent first.)"


def _specialist_system_prompt(role: AgentRoleConfig, base_prompt: str) -> str:
    return (
        f"你是 {role.name}。\n"
        f"职责边界：{role.responsibility}\n"
        f"上下文策略：{role.default_context_strategy}\n\n"
        f"{base_prompt}"
    )


def _delegation_event(task: AgentTask, role: AgentRoleConfig, status: str) -> dict[str, Any]:
    return {
        "type": "agent_delegation",
        "data": {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "target_agent_id": task.target_agent_id,
            "target_agent_name": role.name,
            "status": status,
        },
    }


def _resolve_assistant_role(request: AssistantChatRequest, registry: AgentRegistry) -> AgentRoleConfig:
    task_type = _assistant_task_type(request)
    role = registry.resolve(task_type)
    if role.agent_id == WRITING_AGENT_ID:
        return role
    return role


async def stream_assistant_with_multi_agent(
    *,
    session: Session,
    request: AssistantChatRequest,
    system_prompt: str,
    registry: AgentRegistry = DEFAULT_AGENT_REGISTRY,
) -> AsyncGenerator[dict, None]:
    role = _resolve_assistant_role(request, registry)
    requested_tools = list(getattr(request, "agent_requested_tools", None) or role.allowed_tool_names)
    ensure_allowed_tool_scope(role, requested_tools)
    task = build_delegated_task(
        task_type=_assistant_task_type(request),
        target_agent_id=role.agent_id,
        content=request.user_prompt or "",
        route_key=_assistant_task_type(request),
        requested_tool_names=requested_tools,
        context={"project_id": request.project_id},
    )

    yield _delegation_event(task, role, "running")
    output_parts: list[str] = []
    try:
        async for event in _stream_specialist(session, request, system_prompt, role, requested_tools):
            if event.get("type") == "token":
                data = event.get("data") or {}
                output_parts.append(str(data.get("text") or ""))
            yield event
    except Exception as exc:
        result = build_failed_result(task, str(exc))
        logger.error("[MultiAgent] delegated task failed: {}", result.model_dump())
        failed_event = _delegation_event(task, role, "failed")
        failed_event["data"]["result"] = result.model_dump(mode="json")
        yield failed_event
        raise

    result = build_success_result(task, "".join(output_parts))
    end_event = _delegation_event(task, role, "succeeded")
    end_event["data"]["result"] = result.model_dump(mode="json")
    yield end_event


async def _stream_specialist(
    session: Session,
    request: AssistantChatRequest,
    system_prompt: str,
    role: AgentRoleConfig,
    requested_tools: list[str],
) -> AsyncGenerator[dict, None]:
    deps = AssistantDeps(session=session, project_id=request.project_id)
    tools = get_assistant_tools(allowed_tool_names=requested_tools)
    async for event in stream_agent_with_tools(
        session=session,
        llm_config_id=request.llm_config_id,
        system_prompt=_specialist_system_prompt(role, system_prompt),
        user_prompt=_assistant_user_prompt(request),
        tools=tools,
        set_deps=set_assistant_deps,
        deps=deps,
        temperature=request.temperature or 0.6,
        max_tokens=16384 if request.max_tokens is None else request.max_tokens,
        timeout=request.timeout or 90,
        thinking_enabled=getattr(request, "thinking_enabled", None),
        enable_summarization=bool(getattr(request, "context_summarization_enabled", None)),
        max_tokens_before_summary=getattr(request, "context_summarization_threshold", None) or 8192,
        log_tag=f"MultiAgent:{role.agent_id}",
    ):
        yield event
