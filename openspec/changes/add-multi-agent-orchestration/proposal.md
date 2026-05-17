## Why

`NovelForge` 当前已经具备单一助手、工作流节点和若干专用 AI 提取链路，但这些能力主要仍以“一个入口 + 多种 prompt/工具模式”的方式组织。随着写作助手、审核、关系抽取、记忆提取、后续知识注入逐步增多，继续把所有行为堆在单 agent 中，会让提示词膨胀、工具选择变混乱、上下文边界不清晰。

将多 agent 能力拆成独立变更，有助于先建立“角色分工、路由规则、上下文边界、协作结果回流”的清晰模型，为后续能力扩展提供稳定骨架，而不是继续在单入口里叠加条件分支。

## What Changes

- 为 `NovelForge` 引入可配置的多 agent 编排模型，支持至少一个主 agent 和多个专职 agent 的角色定义。
- 定义 agent 的职责边界、可用工具集合、推荐上下文范围和结果回传机制。
- 在现有助手/工作流体系上新增 agent 路由与协作流程，而不是替换现有全部 AI 入口。
- 为多 agent 协作增加显式的任务委派、执行状态和结果聚合契约。
- 本次变更为架构增量，不要求一次交付完整 UI 工作台，也不要求实现并行执行优化。

## Capabilities

### New Capabilities
- `multi-agent-orchestration`: 为写作、审校、抽取等场景提供具备角色分工、任务委派和结果汇总能力的多 agent 编排机制。

### Modified Capabilities
- 无

## Impact

- 后端助手服务：`backend/app/services/ai/assistant/`
- 后端 AI 核心流：`backend/app/services/ai/core/`
- 工作流/agent 接口：`backend/app/api/endpoints/workflow_agent.py`
- 前端助手与 AI 交互面板：`frontend/src/renderer/src/`
- 提示词与 agent 配置管理：`backend/app/bootstrap/prompts.py` 及相关配置模型
