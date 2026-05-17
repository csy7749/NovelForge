from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.prompt import KnowledgeCreate, KnowledgeMetadata, KnowledgeRead, KnowledgeUpdate
from app.schemas.response import ApiResponse
from app.services.knowledge_service import (
    KnowledgeMutation,
    KnowledgeSearchOptions,
    KnowledgeService,
    SUPPORTED_INJECTION_MODES,
    SUPPORTED_KNOWLEDGE_TYPES,
    SUPPORTED_RETRIEVAL_BACKENDS,
)

router = APIRouter()


@router.get("/meta", response_model=ApiResponse[KnowledgeMetadata], summary="获取知识系统元信息")
def get_knowledge_metadata():
    return ApiResponse(data=KnowledgeMetadata(
        knowledge_types=list(SUPPORTED_KNOWLEDGE_TYPES),
        injection_modes=list(SUPPORTED_INJECTION_MODES),
        retrieval_backends=list(SUPPORTED_RETRIEVAL_BACKENDS),
    ))


@router.get("/", response_model=ApiResponse[List[KnowledgeRead]], summary="获取知识库列表")
def list_knowledge(request: Request, session: Session = Depends(get_session)):
    return _list_knowledge(request, session)


@router.get("/search", response_model=ApiResponse[List[KnowledgeRead]], summary="检索知识文档")
def search_knowledge(request: Request, session: Session = Depends(get_session)):
    return _list_knowledge(request, session)


@router.post("/", response_model=ApiResponse[KnowledgeRead], summary="创建知识库")
def create_knowledge(body: KnowledgeCreate, session: Session = Depends(get_session)):
    svc = KnowledgeService(session)
    if svc.get_by_name(body.name):
        raise HTTPException(status_code=400, detail="同名知识库已存在")
    item = _call_service(lambda: svc.create(KnowledgeMutation(body.model_dump())))
    return ApiResponse(data=item)


@router.get("/{kid}", response_model=ApiResponse[KnowledgeRead], summary="获取单个知识库")
def get_knowledge(kid: int, session: Session = Depends(get_session)):
    item = KnowledgeService(session).get_by_id(kid)
    if not item:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return ApiResponse(data=item)


@router.put("/{kid}", response_model=ApiResponse[KnowledgeRead], summary="更新知识库")
def update_knowledge(kid: int, body: KnowledgeUpdate, session: Session = Depends(get_session)):
    svc = KnowledgeService(session)
    _ensure_unique_name(svc, body.name, kid)
    payload = body.model_dump(exclude_unset=True)
    item = _call_service(lambda: svc.update(kid, KnowledgeMutation(payload)))
    if not item:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return ApiResponse(data=item)


@router.delete("/{kid}", response_model=ApiResponse, summary="删除知识库")
def delete_knowledge(kid: int, session: Session = Depends(get_session)):
    svc = KnowledgeService(session)
    item = svc.get_by_id(kid)
    if not item:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if getattr(item, "built_in", False):
        raise HTTPException(status_code=400, detail="系统内置知识库不可删除")
    _call_service(lambda: svc.delete(kid))
    return ApiResponse(message="删除成功")


def _list_knowledge(request: Request, session: Session):
    options = _search_options_from_request(request)
    items = _call_service(lambda: KnowledgeService(session).list(options))
    return ApiResponse(data=items)


def _search_options_from_request(request: Request) -> KnowledgeSearchOptions:
    query = request.query_params
    return KnowledgeSearchOptions(
        knowledge_type=query.get("knowledge_type") or None,
        query=query.get("query") or None,
        is_injectable=_parse_optional_bool(query.get("is_injectable")),
        retrieval_backend=query.get("retrieval_backend") or "keyword",
    )


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    normalized = value.lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise HTTPException(status_code=422, detail=f"无效布尔值: {value}")


def _ensure_unique_name(svc: KnowledgeService, name: str | None, current_id: int) -> None:
    if not name:
        return
    existing = svc.get_by_name(name)
    if existing and existing.id != current_id:
        raise HTTPException(status_code=400, detail="同名知识库已存在")


def _call_service(action):
    try:
        return action()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
