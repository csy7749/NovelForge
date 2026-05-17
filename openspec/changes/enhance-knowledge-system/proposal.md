## Why

`NovelForge` 当前已经有 `knowledge` CRUD、若干内置知识导入，以及 `memory`/图谱型事实装配，但它还不是一个真正分层、可检索、可注入、可维护的知识系统。现在的短板主要不是“完全没有知识”，而是“知识类型混杂、注入策略粗糙、检索和维护能力弱”。

把知识库增强拆成独立 change，可以先建立知识文档分类、注入模式、摘要/检索层和维护边界。这样既能为上下文可视化提供更丰富来源，也能为后续 agent 提供更稳定的长期知识底座。

## What Changes

- 将知识系统从单纯的条目 CRUD 增强为分类型知识文档体系，支持至少 `design / memory / skill / reference` 四类语义分层。
- 为知识条目增加注入模式、摘要能力和可配置的维护边界。
- 增加知识检索能力，支持最小可用的关键词/结构化检索，并为后续语义检索预留扩展口。
- 明确知识系统与现有 `memory` 图谱、上下文装配、AI 注入链路之间的边界和协作方式。
- 本次变更不要求一次引入完整 embedding/向量系统，但要求定义通往该能力的稳定模型。

## Capabilities

### New Capabilities
- `knowledge-system`: 为项目提供分层知识文档、注入策略、摘要与检索能力的知识系统基础设施。

### Modified Capabilities
- 无

## Impact

- 后端知识接口与服务：`backend/app/api/endpoints/knowledge.py`、`backend/app/services/knowledge_service.py`
- 启动导入与内置知识：`backend/app/bootstrap/knowledge.py`
- 上下文装配与 AI 注入链路
- 前端知识管理与相关设置入口
