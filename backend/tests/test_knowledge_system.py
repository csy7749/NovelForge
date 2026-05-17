from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import KGRelation
from app.services.knowledge_service import (
    KnowledgeMutation,
    KnowledgeSearchOptions,
    KnowledgeService,
)
from app.services.prompt_service import inject_knowledge


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_typed_knowledge_can_be_created_and_searched() -> None:
    with _session() as session:
        service = KnowledgeService(session)
        service.create(KnowledgeMutation({
            "name": "写作规则",
            "content": "固定使用第三人称有限视角",
            "knowledge_type": "design",
        }))

        results = service.list(KnowledgeSearchOptions(knowledge_type="design", query="第三人称"))

        assert len(results) == 1
        assert results[0].knowledge_type == "design"


def test_injectable_block_uses_summary_mode_only_for_enabled_documents() -> None:
    with _session() as session:
        service = KnowledgeService(session)
        service.create(KnowledgeMutation({
            "name": "长期风格",
            "content": "完整风格说明",
            "summary": "短摘要",
            "knowledge_type": "reference",
            "is_injectable": True,
            "injection_mode": "summary",
        }))
        service.create(KnowledgeMutation({
            "name": "内部草稿",
            "content": "不应自动注入",
            "knowledge_type": "reference",
        }))

        block = service.render_injectable_block()

        assert "短摘要" in block
        assert "不应自动注入" not in block


def test_summary_injection_requires_summary() -> None:
    with _session() as session:
        service = KnowledgeService(session)

        with _assert_raises(ValueError, "必须提供摘要"):
            service.create(KnowledgeMutation({
                "name": "缺摘要",
                "content": "正文",
                "is_injectable": True,
                "injection_mode": "summary",
            }))


def test_semantic_retrieval_is_reserved_but_not_silently_used() -> None:
    with _session() as session:
        service = KnowledgeService(session)

        with _assert_raises(ValueError, "semantic 检索接口已预留"):
            service.list(KnowledgeSearchOptions(retrieval_backend="semantic"))


def test_knowledge_service_does_not_write_memory_graph_relations() -> None:
    with _session() as session:
        service = KnowledgeService(session)
        service.create(KnowledgeMutation({
            "name": "稳定设定",
            "content": "这是长期规则，不是动态图谱事实",
            "knowledge_type": "memory",
        }))

        relations = session.exec(select(KGRelation)).all()

        assert relations == []


def test_prompt_injection_adds_only_enabled_documents_by_default() -> None:
    with _session() as session:
        service = KnowledgeService(session)
        service.create(KnowledgeMutation({
            "name": "启用知识",
            "content": "自动注入内容",
            "knowledge_type": "skill",
            "is_injectable": True,
            "injection_mode": "full",
        }))
        service.create(KnowledgeMutation({
            "name": "禁用知识",
            "content": "不自动注入内容",
            "knowledge_type": "reference",
        }))

        rendered = inject_knowledge(session, "- knowledge:")

        assert "自动注入内容" in rendered
        assert "不自动注入内容" not in rendered


class _assert_raises:
    def __init__(self, error_type: type[Exception], message_part: str) -> None:
        self.error_type = error_type
        self.message_part = message_part

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc is None:
            raise AssertionError(f"Expected {self.error_type.__name__}")
        if not isinstance(exc, self.error_type):
            return False
        if self.message_part not in str(exc):
            raise AssertionError(f"Expected message containing {self.message_part!r}, got {exc}")
        return True


if __name__ == "__main__":
    test_typed_knowledge_can_be_created_and_searched()
    test_injectable_block_uses_summary_mode_only_for_enabled_documents()
    test_summary_injection_requires_summary()
    test_semantic_retrieval_is_reserved_but_not_silently_used()
    test_knowledge_service_does_not_write_memory_graph_relations()
    test_prompt_injection_adds_only_enabled_documents_by_default()
