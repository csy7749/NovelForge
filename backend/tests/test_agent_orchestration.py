from __future__ import annotations

import unittest

from app.schemas.agent_orchestration import AgentRoleConfig
from app.services.ai.orchestration import (
    DEFAULT_AGENT_REGISTRY,
    MEMORY_AGENT_ID,
    REVIEW_AGENT_ID,
    WRITING_AGENT_ID,
    AgentToolAuthorizationError,
    build_delegated_task,
    build_failed_result,
    build_success_result,
    ensure_allowed_tool_scope,
)


class AgentOrchestrationTests(unittest.TestCase):
    def test_default_registry_resolves_specialist_routes(self) -> None:
        self.assertEqual(DEFAULT_AGENT_REGISTRY.resolve("writing").agent_id, WRITING_AGENT_ID)
        self.assertEqual(DEFAULT_AGENT_REGISTRY.resolve("relation").agent_id, MEMORY_AGENT_ID)
        self.assertEqual(DEFAULT_AGENT_REGISTRY.resolve("review").agent_id, REVIEW_AGENT_ID)

    def test_registry_requires_explicit_role_definition(self) -> None:
        role = DEFAULT_AGENT_REGISTRY.get(WRITING_AGENT_ID)

        self.assertEqual(role.role, "specialist")
        self.assertTrue(role.responsibility)
        self.assertTrue(role.default_context_strategy)
        self.assertIn("create_card", role.allowed_tool_names)

    def test_tool_scope_blocks_disallowed_tools(self) -> None:
        role = AgentRoleConfig(
            agent_id="limited_agent",
            name="有限 Agent",
            role="specialist",
            responsibility="只允许读取。",
            allowed_tool_names=("search_cards",),
        )

        with self.assertRaises(AgentToolAuthorizationError):
            ensure_allowed_tool_scope(role, ["search_cards", "delete_card"])

    def test_delegated_task_and_results_keep_source_agent(self) -> None:
        task = build_delegated_task(
            task_type="review",
            target_agent_id=REVIEW_AGENT_ID,
            content="检查章节节奏。",
        )

        success = build_success_result(task, "已完成")
        failed = build_failed_result(task, "模型调用失败")

        self.assertEqual(success.task_id, task.task_id)
        self.assertEqual(success.source_agent_id, REVIEW_AGENT_ID)
        self.assertEqual(success.status, "succeeded")
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error, "模型调用失败")
