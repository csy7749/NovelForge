from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.ai_trace import TraceRunCreate, TraceRunRead, TraceStepRead
from app.services.ai_trace_service import get_ai_trace_service


router = APIRouter()


@router.post("/runs", response_model=TraceRunRead)
def create_trace_run(
    request: TraceRunCreate,
    session: Session = Depends(get_session),
) -> TraceRunRead:
    return get_ai_trace_service(session).create_run(request)


@router.get("/runs", response_model=list[TraceRunRead])
def list_trace_runs(
    project_id: Optional[int] = Query(default=None),
    card_id: Optional[int] = Query(default=None),
    entrypoint: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[TraceRunRead]:
    query = {
        "project_id": project_id,
        "card_id": card_id,
        "entrypoint": entrypoint,
        "limit": limit,
    }
    return get_ai_trace_service(session).list_runs(query)


@router.get("/runs/{run_id}", response_model=TraceRunRead)
def get_trace_run(
    run_id: str,
    session: Session = Depends(get_session),
) -> TraceRunRead:
    try:
        return get_ai_trace_service(session).get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/steps", response_model=list[TraceStepRead])
def list_trace_steps(
    run_id: str,
    session: Session = Depends(get_session),
) -> list[TraceStepRead]:
    return get_ai_trace_service(session).list_steps(run_id)
