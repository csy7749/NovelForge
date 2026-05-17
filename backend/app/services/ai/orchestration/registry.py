from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.schemas.agent_orchestration import AgentRoleConfig


PRIMARY_AGENT_ID = "primary_orchestrator"
WRITING_AGENT_ID = "writing_specialist"
MEMORY_AGENT_ID = "memory_extraction_specialist"
REVIEW_AGENT_ID = "review_specialist"

WRITING_TOOL_SCOPE = (
    "search_cards",
    "get_card_content",
    "get_card_type_schema",
    "create_card",
    "update_card",
    "modify_card_field",
    "replace_card_text_by_lines",
    "replace_field_text",
    "list_reviews_for_target",
    "get_review_record",
)


def _role_items() -> tuple[AgentRoleConfig, ...]:
    return (
        AgentRoleConfig(
            agent_id=PRIMARY_AGENT_ID,
            name="主编排 Agent",
            role="primary",
            responsibility="识别任务类型、建立委派边界并汇总专职 agent 结果。",
            route_keys=("primary", "orchestrator"),
            default_context_strategy="routing_summary",
        ),
        AgentRoleConfig(
            agent_id=WRITING_AGENT_ID,
            name="写作专职 Agent",
            role="specialist",
            responsibility="处理小说设定、卡片创建/修改、正文改写等创作执行任务。",
            route_keys=("assistant", "writing", "card", "rewrite"),
            allowed_tool_names=WRITING_TOOL_SCOPE,
            default_context_strategy="project_context",
            prompt_name="灵感对话",
        ),
        AgentRoleConfig(
            agent_id=MEMORY_AGENT_ID,
            name="关系与记忆抽取 Agent",
            role="specialist",
            responsibility="从正文中提取关系、角色动态信息与可写回记忆，不执行卡片写入。",
            route_keys=("memory", "memory_extraction", "relation", "relation_extraction"),
            default_context_strategy="chapter_bound",
        ),
        AgentRoleConfig(
            agent_id=REVIEW_AGENT_ID,
            name="审校专职 Agent",
            role="specialist",
            responsibility="审核章节、卡片或片段，输出质量门结论和修改建议。",
            route_keys=("review", "audit", "chapter_review", "card_review"),
            default_context_strategy="review_target_bound",
            prompt_name="通用审核",
        ),
    )


@dataclass(frozen=True)
class AgentRegistry:
    roles: tuple[AgentRoleConfig, ...]

    def get(self, agent_id: str) -> AgentRoleConfig:
        for item in self.roles:
            if item.agent_id == agent_id:
                return item
        raise KeyError(f"未知 agent: {agent_id}")

    def list(self) -> list[AgentRoleConfig]:
        return list(self.roles)

    def resolve(self, route_key: str) -> AgentRoleConfig:
        normalized = route_key.strip().lower()
        for item in self.roles:
            if normalized in item.route_keys:
                return item
        raise KeyError(f"未配置 agent 路由: {route_key}")

    def register(self, role: AgentRoleConfig) -> "AgentRegistry":
        kept = tuple(item for item in self.roles if item.agent_id != role.agent_id)
        return AgentRegistry(roles=kept + (role,))

    def allowed_tool_names(self, agent_id: str) -> frozenset[str]:
        return frozenset(self.get(agent_id).allowed_tool_names)


def build_agent_registry(roles: Iterable[AgentRoleConfig] | None = None) -> AgentRegistry:
    return AgentRegistry(roles=tuple(roles or _role_items()))


DEFAULT_AGENT_REGISTRY = build_agent_registry()
