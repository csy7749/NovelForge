from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


AgentRole = Literal["primary", "specialist"]
AgentTaskStatus = Literal["pending", "running", "succeeded", "failed", "blocked"]


class AgentRoleConfig(BaseModel):
    agent_id: str
    name: str
    role: AgentRole
    responsibility: str
    route_keys: tuple[str, ...] = Field(default_factory=tuple)
    allowed_tool_names: tuple[str, ...] = Field(default_factory=tuple)
    default_context_strategy: str = "bounded"
    prompt_name: str | None = None

    model_config = {"frozen": True}


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str
    target_agent_id: str
    content: str
    source_agent_id: str = "primary_orchestrator"
    route_key: str | None = None
    requested_tool_names: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: str
    source_agent_id: str
    status: AgentTaskStatus
    content: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
