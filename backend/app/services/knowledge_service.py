from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import or_
from sqlmodel import Session, select

from app.db.models import Knowledge

SUPPORTED_KNOWLEDGE_TYPES = ("design", "memory", "skill", "reference")
SUPPORTED_INJECTION_MODES = ("none", "full", "summary")
SUPPORTED_RETRIEVAL_BACKENDS = ("keyword", "semantic")
IMPLEMENTED_RETRIEVAL_BACKENDS = ("keyword",)
SEARCHABLE_FIELDS = (
    Knowledge.name,
    Knowledge.description,
    Knowledge.content,
    Knowledge.summary,
)


@dataclass(frozen=True)
class KnowledgeMutation:
    values: dict[str, Any]


@dataclass(frozen=True)
class KnowledgeSearchOptions:
    skip: int = 0
    limit: int = 200
    knowledge_type: Optional[str] = None
    query: Optional[str] = None
    is_injectable: Optional[bool] = None
    retrieval_backend: str = "keyword"


class KnowledgeService:
    """知识库服务：提供 typed knowledge document 的增删改查和检索。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, options: KnowledgeSearchOptions | None = None) -> List[Knowledge]:
        search_options = options or KnowledgeSearchOptions()
        statement = self._build_search_statement(search_options)
        return self.db.exec(statement.offset(search_options.skip).limit(search_options.limit)).all()

    def get_by_id(self, kid: int) -> Optional[Knowledge]:
        return self.db.get(Knowledge, kid)

    def get_by_name(self, name: str) -> Optional[Knowledge]:
        return self.db.exec(select(Knowledge).where(Knowledge.name == name)).first()

    def create(self, mutation: KnowledgeMutation) -> Knowledge:
        values = dict(mutation.values)
        kb = _build_knowledge(values)
        _validate_document(kb)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def update(self, kid: int, mutation: KnowledgeMutation) -> Optional[Knowledge]:
        kb = self.get_by_id(kid)
        if not kb:
            return None
        for key, value in mutation.values.items():
            setattr(kb, key, value)
        kb.updated_at = datetime.now()
        _validate_document(kb)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def delete(self, kid: int) -> bool:
        kb = self.get_by_id(kid)
        if not kb:
            return False
        if getattr(kb, "built_in", False):
            raise ValueError("系统内置知识库不可删除")
        self.db.delete(kb)
        self.db.commit()
        return True

    def render_content_for_injection(self, kb: Knowledge) -> str:
        _validate_document(kb)
        if kb.injection_mode == "summary":
            return (kb.summary or "").strip()
        return (kb.content or "").strip()

    def render_injectable_block(self) -> str:
        items = self.list(KnowledgeSearchOptions(is_injectable=True, limit=1000))
        if not items:
            return ""
        entries = [_format_injectable_item(item, self.render_content_for_injection(item)) for item in items]
        return "【知识文档】\n" + "\n\n".join(entries)

    def _build_search_statement(self, options: KnowledgeSearchOptions):
        _validate_search_options(options)
        statement = select(Knowledge)
        if options.knowledge_type:
            statement = statement.where(Knowledge.knowledge_type == options.knowledge_type)
        if options.is_injectable is not None:
            statement = statement.where(Knowledge.is_injectable == options.is_injectable)
        if options.query:
            statement = statement.where(_query_condition(options.query))
        return statement.order_by(Knowledge.name)


def _build_knowledge(values: dict[str, Any]) -> Knowledge:
    now = datetime.now()
    return Knowledge(
        name=_required_text(values, "name"),
        description=values.get("description"),
        content=_required_text(values, "content"),
        built_in=bool(values.get("built_in", False)),
        knowledge_type=values.get("knowledge_type", "reference"),
        summary=values.get("summary"),
        summary_enabled=bool(values.get("summary_enabled", False)),
        is_injectable=bool(values.get("is_injectable", False)),
        injection_mode=values.get("injection_mode", "none"),
        injection_config=values.get("injection_config"),
        source=values.get("source"),
        maintenance_notes=values.get("maintenance_notes"),
        updated_at=now,
    )


def _required_text(values: dict[str, Any], key: str) -> str:
    value = str(values.get(key) or "").strip()
    if not value:
        raise ValueError(f"知识文档字段不能为空: {key}")
    return value


def _validate_document(kb: Knowledge) -> None:
    if kb.knowledge_type not in SUPPORTED_KNOWLEDGE_TYPES:
        raise ValueError(f"不支持的知识类型: {kb.knowledge_type}")
    if kb.injection_mode not in SUPPORTED_INJECTION_MODES:
        raise ValueError(f"不支持的注入模式: {kb.injection_mode}")
    if kb.is_injectable and kb.injection_mode == "none":
        raise ValueError("启用注入时必须选择 full 或 summary 注入模式")
    if kb.injection_mode == "summary" and not (kb.summary or "").strip():
        raise ValueError("summary 注入模式必须提供摘要")


def _validate_search_options(options: KnowledgeSearchOptions) -> None:
    if options.knowledge_type and options.knowledge_type not in SUPPORTED_KNOWLEDGE_TYPES:
        raise ValueError(f"不支持的知识类型: {options.knowledge_type}")
    if options.retrieval_backend not in SUPPORTED_RETRIEVAL_BACKENDS:
        raise ValueError(f"不支持的检索后端: {options.retrieval_backend}")
    if options.retrieval_backend not in IMPLEMENTED_RETRIEVAL_BACKENDS:
        raise ValueError("semantic 检索接口已预留，但当前变更未实现向量检索运行时")


def _query_condition(query: str):
    pattern = f"%{query.strip()}%"
    return or_(*(field.ilike(pattern) for field in SEARCHABLE_FIELDS))


def _format_injectable_item(kb: Knowledge, content: str) -> str:
    title = f"- [{kb.knowledge_type}] {kb.name}"
    description = (kb.description or "").strip()
    header = f"{title}\n  {description}" if description else title
    return f"{header}\n{content}"
