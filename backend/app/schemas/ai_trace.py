from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TraceRunStatus = Literal["running", "succeeded", "failed", "cancelled"]
TraceStepStatus = Literal["running", "succeeded", "failed", "skipped"]
TraceStepKind = Literal["tool", "pipeline", "context", "generation", "review", "model", "error"]


class TraceJumpTarget(BaseModel):
    type: str
    id: Optional[str] = None
    project_id: Optional[int] = None
    card_id: Optional[int] = None
    entity_name: Optional[str] = None
    knowledge_id: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TraceSourceCreate(BaseModel):
    source_type: str
    source_ref: Optional[str] = None
    label: str
    preview: Optional[str] = None
    jump_target: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceSpanCreate(BaseModel):
    source_id: str
    start_offset: int
    end_offset: int
    text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceRunCreate(BaseModel):
    project_id: Optional[int] = None
    card_id: Optional[int] = None
    entrypoint: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceStepCreate(BaseModel):
    run_id: str
    name: str
    kind: TraceStepKind
    input_payload: Any = None
    input_schema: Optional[dict[str, Any]] = None
    external_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceStepFinish(BaseModel):
    step_id: Optional[str] = None
    run_id: Optional[str] = None
    external_id: Optional[str] = None
    status: TraceStepStatus = "succeeded"
    output_payload: Any = None
    output_schema: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    sources: list[TraceSourceCreate] = Field(default_factory=list)
    spans: list[TraceSpanCreate] = Field(default_factory=list)


class TraceSpanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_id: str
    source_id: str
    start_offset: int
    end_offset: int
    text: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class TraceSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_id: str
    source_type: str
    source_ref: Optional[str] = None
    label: str
    preview: Optional[str] = None
    jump_target: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    spans: list[TraceSpanRead] = Field(default_factory=list)


class TraceStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    name: str
    kind: str
    status: str
    timestamp: datetime
    started_at: datetime
    ended_at: Optional[datetime] = None
    external_id: Optional[str] = None
    input_summary: Optional[dict[str, Any]] = None
    output_summary: Optional[dict[str, Any]] = None
    input_schema: Optional[dict[str, Any]] = None
    output_schema: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    sources: list[TraceSourceRead] = Field(default_factory=list)


class TraceRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: Optional[int] = None
    card_id: Optional[int] = None
    entrypoint: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None
    steps: list[TraceStepRead] = Field(default_factory=list)
