from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from loguru import logger
from sqlmodel import Session, select

from app.core.config import settings
from app.db.models import AITraceRun, AITraceSource, AITraceSpan, AITraceStep
from app.schemas.ai_trace import (
    TraceRunCreate,
    TraceRunRead,
    TraceSourceCreate,
    TraceSourceRead,
    TraceSpanCreate,
    TraceSpanRead,
    TraceStepCreate,
    TraceStepFinish,
    TraceStepRead,
)


MAX_SUMMARY_DEPTH = 3
MAX_SUMMARY_ITEMS = 8
MAX_SUMMARY_TEXT = 500
SECRET_KEY_PARTS = ("key", "token", "secret", "password", "credential", "api_key")
SOURCE_FIELDS = ("knowledge_sources", "sources", "references")
SPAN_FIELDS = ("output_spans", "source_spans", "spans")


class TraceRepository(Protocol):
    def create_run(self, data: TraceRunCreate) -> AITraceRun: ...
    def finish_run(self, run_id: str, status: str, error: str | None = None) -> AITraceRun: ...
    def start_step(self, data: TraceStepCreate, input_summary: dict[str, Any]) -> AITraceStep: ...
    def finish_step(self, data: TraceStepFinish, output_summary: dict[str, Any]) -> AITraceStep: ...
    def add_sources(self, step_id: str, sources: list[TraceSourceCreate]) -> list[AITraceSource]: ...
    def add_spans(self, step_id: str, spans: list[TraceSpanCreate]) -> list[AITraceSpan]: ...
    def get_run(self, run_id: str) -> AITraceRun | None: ...
    def list_runs(self, query: dict[str, Any]) -> list[AITraceRun]: ...
    def list_steps(self, run_id: str) -> list[AITraceStep]: ...
    def list_sources(self, step_id: str) -> list[AITraceSource]: ...
    def list_spans(self, step_id: str) -> list[AITraceSpan]: ...


def _now() -> datetime:
    return datetime.now()


def _new_id() -> str:
    return str(uuid4())


def _preview_text(value: str, limit: int = MAX_SUMMARY_TEXT) -> str:
    text = value.replace("\r\n", "\n").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...（已截断，原长度 {len(text)}）"


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEY_PARTS)


def _safe_value(value: Any, depth: int = 0) -> Any:
    if depth >= MAX_SUMMARY_DEPTH:
        return _summarize_leaf(value)
    if isinstance(value, dict):
        return _safe_dict(value, depth)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, depth + 1) for item in list(value)[:MAX_SUMMARY_ITEMS]]
    if isinstance(value, str):
        return _preview_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _preview_text(str(value), 160)


def _safe_dict(value: dict[str, Any], depth: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for index, (key, item) in enumerate(value.items()):
        if index >= MAX_SUMMARY_ITEMS:
            result["_truncated_keys"] = len(value) - MAX_SUMMARY_ITEMS
            break
        result[key] = "***REDACTED***" if _is_secret_key(str(key)) else _safe_value(item, depth + 1)
    return result


def _summarize_leaf(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"type": "object", "keys": list(value.keys())[:MAX_SUMMARY_ITEMS]}
    if isinstance(value, (list, tuple)):
        return {"type": "array", "count": len(value)}
    if isinstance(value, str):
        return {"type": "text", "preview": _preview_text(value, 160), "length": len(value)}
    return {"type": type(value).__name__, "preview": _preview_text(str(value), 160)}


def summarize_payload(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {"type": "empty"}
    if isinstance(payload, dict):
        return {"type": "object", "value": _safe_dict(payload, 0)}
    if isinstance(payload, (list, tuple)):
        return {"type": "array", "count": len(payload), "items": _safe_value(payload)}
    if isinstance(payload, str):
        return {"type": "text", "preview": _preview_text(payload), "length": len(payload)}
    return {"type": type(payload).__name__, "value": _safe_value(payload)}


def _source_from_dict(raw: dict[str, Any]) -> TraceSourceCreate:
    source_type = str(raw.get("source_type") or raw.get("type") or raw.get("kind") or "reference")
    source_ref = raw.get("source_ref") or raw.get("ref") or raw.get("id") or raw.get("card_id")
    label = raw.get("label") or raw.get("title") or raw.get("name") or source_ref or source_type
    preview = raw.get("preview") or raw.get("summary") or raw.get("content") or raw.get("text")
    return TraceSourceCreate(
        source_type=source_type,
        source_ref=str(source_ref) if source_ref is not None else None,
        label=str(label),
        preview=_preview_text(str(preview), 240) if preview is not None else None,
        jump_target=_normalize_jump_target(raw),
        metadata={k: _safe_value(v) for k, v in raw.items() if k not in SOURCE_FIELDS},
    )


def _normalize_jump_target(raw: dict[str, Any]) -> dict[str, Any] | None:
    target = raw.get("jump_target")
    if isinstance(target, dict):
        return _safe_dict(target, 0)
    if raw.get("card_id") is not None:
        return {"type": "card", "card_id": raw.get("card_id"), "project_id": raw.get("project_id")}
    if raw.get("knowledge_id") is not None:
        return {"type": "knowledge", "knowledge_id": str(raw.get("knowledge_id"))}
    if raw.get("entity_name") is not None:
        return {"type": "graph_entity", "entity_name": str(raw.get("entity_name"))}
    return None


def _source_from_any(raw: Any) -> TraceSourceCreate:
    if isinstance(raw, TraceSourceCreate):
        return raw
    if isinstance(raw, dict):
        return _source_from_dict(raw)
    return TraceSourceCreate(source_type="reference", label=_preview_text(str(raw), 120))


def _extract_source_values(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    values: list[Any] = []
    for field in SOURCE_FIELDS:
        item = payload.get(field)
        if item is not None:
            values.extend(item if isinstance(item, list) else [item])
    for nested_key in ("result", "data"):
        values.extend(_extract_source_values(payload.get(nested_key)))
    return values


def normalize_sources(payload: Any, extra: list[TraceSourceCreate] | None = None) -> list[TraceSourceCreate]:
    sources = [_source_from_any(item) for item in _extract_source_values(payload)]
    sources.extend(extra or [])
    return sources


def _extract_spans(payload: Any) -> list[TraceSpanCreate]:
    if not isinstance(payload, dict):
        return []
    spans: list[TraceSpanCreate] = []
    for field in SPAN_FIELDS:
        raw_items = payload.get(field)
        if isinstance(raw_items, list):
            spans.extend(_span_from_dict(item) for item in raw_items if isinstance(item, dict))
    return spans


def _span_from_dict(raw: dict[str, Any]) -> TraceSpanCreate:
    return TraceSpanCreate(
        source_id=str(raw.get("source_id") or ""),
        start_offset=int(raw.get("start_offset") or raw.get("start") or 0),
        end_offset=int(raw.get("end_offset") or raw.get("end") or 0),
        text=str(raw.get("text")) if raw.get("text") is not None else None,
        metadata={k: _safe_value(v) for k, v in raw.items()},
    )


class InMemoryTraceRepository:
    def __init__(self) -> None:
        self.runs: dict[str, AITraceRun] = {}
        self.steps: dict[str, AITraceStep] = {}
        self.sources: dict[str, AITraceSource] = {}
        self.spans: dict[str, AITraceSpan] = {}

    def create_run(self, data: TraceRunCreate) -> AITraceRun:
        raw = data.model_dump(exclude={"metadata"}, mode="json")
        run = AITraceRun(id=_new_id(), **raw, metadata_json=data.metadata)
        self.runs[run.id] = run
        return run

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> AITraceRun:
        run = self._require_run(run_id)
        run.status = status
        run.ended_at = _now()
        run.metadata_json = {**(run.metadata_json or {}), **({"error": error} if error else {})}
        return run

    def start_step(self, data: TraceStepCreate, input_summary: dict[str, Any]) -> AITraceStep:
        step = AITraceStep(id=_new_id(), input_summary=input_summary, **_step_create_kwargs(data))
        self.steps[step.id] = step
        return step

    def finish_step(self, data: TraceStepFinish, output_summary: dict[str, Any]) -> AITraceStep:
        step = self._find_step(data)
        step.status = data.status
        step.ended_at = _now()
        step.output_summary = output_summary
        step.output_schema = data.output_schema
        step.error = data.error
        return step

    def add_sources(self, step_id: str, sources: list[TraceSourceCreate]) -> list[AITraceSource]:
        created = [_make_source(step_id, item) for item in sources]
        self.sources.update({item.id: item for item in created})
        return created

    def add_spans(self, step_id: str, spans: list[TraceSpanCreate]) -> list[AITraceSpan]:
        created = [_make_span(step_id, item) for item in spans if item.source_id]
        self.spans.update({item.id: item for item in created})
        return created

    def get_run(self, run_id: str) -> AITraceRun | None:
        return self.runs.get(run_id)

    def list_runs(self, query: dict[str, Any]) -> list[AITraceRun]:
        items = [run for run in self.runs.values() if _run_matches(run, query)]
        return sorted(items, key=lambda item: item.started_at, reverse=True)[: query["limit"]]

    def list_steps(self, run_id: str) -> list[AITraceStep]:
        items = [step for step in self.steps.values() if step.run_id == run_id]
        return sorted(items, key=lambda item: item.timestamp)

    def list_sources(self, step_id: str) -> list[AITraceSource]:
        return [item for item in self.sources.values() if item.step_id == step_id]

    def list_spans(self, step_id: str) -> list[AITraceSpan]:
        return [item for item in self.spans.values() if item.step_id == step_id]

    def _require_run(self, run_id: str) -> AITraceRun:
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Trace run 不存在: {run_id}")
        return run

    def _find_step(self, data: TraceStepFinish) -> AITraceStep:
        if data.step_id and data.step_id in self.steps:
            return self.steps[data.step_id]
        for step in self.steps.values():
            if step.run_id == data.run_id and step.external_id == data.external_id:
                return step
        raise KeyError("Trace step 不存在，无法完成")


class SQLTraceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(self, data: TraceRunCreate) -> AITraceRun:
        raw = data.model_dump(exclude={"metadata"}, mode="json")
        run = AITraceRun(id=_new_id(), **raw, metadata_json=data.metadata)
        return self._add_and_commit(run)

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> AITraceRun:
        run = self._require_run(run_id)
        run.status = status
        run.ended_at = _now()
        run.metadata_json = {**(run.metadata_json or {}), **({"error": error} if error else {})}
        return self._add_and_commit(run)

    def start_step(self, data: TraceStepCreate, input_summary: dict[str, Any]) -> AITraceStep:
        step = AITraceStep(id=_new_id(), input_summary=input_summary, **_step_create_kwargs(data))
        return self._add_and_commit(step)

    def finish_step(self, data: TraceStepFinish, output_summary: dict[str, Any]) -> AITraceStep:
        step = self._find_step(data)
        step.status = data.status
        step.ended_at = _now()
        step.output_summary = output_summary
        step.output_schema = data.output_schema
        step.error = data.error
        return self._add_and_commit(step)

    def add_sources(self, step_id: str, sources: list[TraceSourceCreate]) -> list[AITraceSource]:
        created = [_make_source(step_id, item) for item in sources]
        for item in created:
            self.session.add(item)
        self._commit()
        return created

    def add_spans(self, step_id: str, spans: list[TraceSpanCreate]) -> list[AITraceSpan]:
        created = [_make_span(step_id, item) for item in spans if item.source_id]
        for item in created:
            self.session.add(item)
        self._commit()
        return created

    def get_run(self, run_id: str) -> AITraceRun | None:
        return self.session.get(AITraceRun, run_id)

    def list_runs(self, query: dict[str, Any]) -> list[AITraceRun]:
        statement = select(AITraceRun).order_by(AITraceRun.started_at.desc()).limit(query["limit"])
        if query.get("project_id") is not None:
            statement = statement.where(AITraceRun.project_id == query["project_id"])
        if query.get("card_id") is not None:
            statement = statement.where(AITraceRun.card_id == query["card_id"])
        if query.get("entrypoint"):
            statement = statement.where(AITraceRun.entrypoint == query["entrypoint"])
        return list(self.session.exec(statement).all())

    def list_steps(self, run_id: str) -> list[AITraceStep]:
        statement = select(AITraceStep).where(AITraceStep.run_id == run_id).order_by(AITraceStep.timestamp)
        return list(self.session.exec(statement).all())

    def list_sources(self, step_id: str) -> list[AITraceSource]:
        statement = select(AITraceSource).where(AITraceSource.step_id == step_id)
        return list(self.session.exec(statement).all())

    def list_spans(self, step_id: str) -> list[AITraceSpan]:
        statement = select(AITraceSpan).where(AITraceSpan.step_id == step_id)
        return list(self.session.exec(statement).all())

    def _add_and_commit(self, item: Any) -> Any:
        self.session.add(item)
        self._commit()
        self.session.refresh(item)
        return item

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            logger.exception("[AITrace] SQLite trace 写入失败")
            raise

    def _require_run(self, run_id: str) -> AITraceRun:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(f"Trace run 不存在: {run_id}")
        return run

    def _find_step(self, data: TraceStepFinish) -> AITraceStep:
        if data.step_id:
            step = self.session.get(AITraceStep, data.step_id)
            if step is not None:
                return step
        statement = _step_lookup_statement(data)
        step = self.session.exec(statement).first()
        if step is None:
            raise KeyError("Trace step 不存在，无法完成")
        return step


def _step_create_kwargs(data: TraceStepCreate) -> dict[str, Any]:
    raw = data.model_dump(exclude={"input_payload", "metadata"}, mode="json")
    return {**raw, "metadata_json": data.metadata}


def _make_source(step_id: str, data: TraceSourceCreate) -> AITraceSource:
    raw = data.model_dump(exclude={"metadata"}, mode="json")
    return AITraceSource(id=_new_id(), step_id=step_id, **raw, metadata_json=data.metadata)


def _make_span(step_id: str, data: TraceSpanCreate) -> AITraceSpan:
    raw = data.model_dump(exclude={"metadata"}, mode="json")
    return AITraceSpan(id=_new_id(), step_id=step_id, **raw, metadata_json=data.metadata)


def _run_matches(run: AITraceRun, query: dict[str, Any]) -> bool:
    if query.get("project_id") is not None and run.project_id != query["project_id"]:
        return False
    if query.get("card_id") is not None and run.card_id != query["card_id"]:
        return False
    if query.get("entrypoint") and run.entrypoint != query["entrypoint"]:
        return False
    return True


def _step_lookup_statement(data: TraceStepFinish):
    statement = select(AITraceStep)
    if data.run_id is not None:
        statement = statement.where(AITraceStep.run_id == data.run_id)
    if data.external_id is not None:
        statement = statement.where(AITraceStep.external_id == data.external_id)
    return statement.order_by(AITraceStep.timestamp.desc())


class AITraceService:
    def __init__(self, repository: TraceRepository) -> None:
        self.repository = repository

    def create_run(self, data: TraceRunCreate) -> TraceRunRead:
        return self._run_read(self.repository.create_run(data))

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> TraceRunRead:
        return self._run_read(self.repository.finish_run(run_id, status, error))

    def start_step(self, data: TraceStepCreate) -> TraceStepRead:
        step = self.repository.start_step(data, summarize_payload(data.input_payload))
        return self._step_read(step)

    def finish_step(self, data: TraceStepFinish) -> TraceStepRead:
        sources = normalize_sources(data.output_payload, data.sources)
        spans = [*_extract_spans(data.output_payload), *data.spans]
        step = self.repository.finish_step(data, summarize_payload(data.output_payload))
        self.repository.add_sources(step.id, sources)
        self.repository.add_spans(step.id, spans)
        return self._step_read(step)

    def fail_step(self, data: TraceStepFinish) -> TraceStepRead:
        failed_data = data.model_copy(update={"status": "failed"})
        return self.finish_step(failed_data)

    def record_event(self, run_id: str, event: dict[str, Any]) -> TraceStepRead | None:
        event_type = str(event.get("type") or "")
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        if event_type == "tool_start":
            return self._record_tool_start(run_id, data)
        if event_type == "tool_end":
            return self._record_tool_end(run_id, data)
        return None

    def list_runs(self, query: dict[str, Any]) -> list[TraceRunRead]:
        return [self._run_read(item, include_steps=True) for item in self.repository.list_runs(query)]

    def get_run(self, run_id: str) -> TraceRunRead:
        run = self.repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Trace run 不存在: {run_id}")
        return self._run_read(run, include_steps=True)

    def list_steps(self, run_id: str) -> list[TraceStepRead]:
        return [self._step_read(step) for step in self.repository.list_steps(run_id)]

    def _record_tool_start(self, run_id: str, data: dict[str, Any]) -> TraceStepRead:
        tool_name = str(data.get("tool_name") or "工具调用")
        return self.start_step(
            TraceStepCreate(
                run_id=run_id,
                name=tool_name,
                kind="tool",
                input_payload=data.get("args") or {},
                external_id=_tool_external_id(data, tool_name),
                metadata={"policy": data.get("policy") or {}},
            )
        )

    def _record_tool_end(self, run_id: str, data: dict[str, Any]) -> TraceStepRead:
        status = "succeeded" if bool(data.get("success", True)) else "failed"
        result = data.get("result") if data.get("result") is not None else data
        return self.finish_step(
            TraceStepFinish(
                run_id=run_id,
                external_id=_tool_external_id(data, str(data.get("tool_name") or "")),
                status=status,
                output_payload=result,
                error=_event_error(result),
            )
        )

    def _run_read(self, run: AITraceRun, include_steps: bool = False) -> TraceRunRead:
        read = TraceRunRead.model_validate(run)
        if include_steps:
            read.steps = self.list_steps(run.id)
        return read

    def _step_read(self, step: AITraceStep) -> TraceStepRead:
        read = TraceStepRead.model_validate(step)
        sources = [TraceSourceRead.model_validate(item) for item in self.repository.list_sources(step.id)]
        spans = [TraceSpanRead.model_validate(item) for item in self.repository.list_spans(step.id)]
        for source in sources:
            source.spans = [span for span in spans if span.source_id == source.id]
        read.sources = sources
        return read


def _tool_external_id(data: dict[str, Any], fallback: str) -> str:
    return str(data.get("call_id") or fallback)


def _event_error(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None
    if result.get("success") is not False:
        return None
    raw = result.get("error") or result.get("message")
    return str(raw) if raw else None


_MEMORY_REPOSITORY = InMemoryTraceRepository()


def get_ai_trace_service(session: Session | None = None) -> AITraceService:
    mode = settings.ai.trace_storage_mode.strip().lower()
    if mode == "memory":
        return AITraceService(_MEMORY_REPOSITORY)
    if mode == "sqlite":
        if session is None:
            raise RuntimeError("AI trace SQLite 模式需要数据库 session")
        return AITraceService(SQLTraceRepository(session))
    raise RuntimeError(f"未知 AI trace 存储模式: {settings.ai.trace_storage_mode}")
