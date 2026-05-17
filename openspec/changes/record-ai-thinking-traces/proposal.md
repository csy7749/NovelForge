## Why

`NovelForge` 的灵感助手、工具调用和后续 Agent 管线会越来越多地参与创作决策，但当前系统缺少一条面向用户和开发者的结构化执行痕迹。用户只能看到最终结果，难以判断 AI 参考了哪些知识、调用了哪些工具、为什么创建或修改某张卡片，也难以在生成偏差时定位问题来源。

在上下文可视化、工具管线规范化和多 Agent 编排逐步成形后，需要补上一层统一的 AI 执行可解释日志，让“上下文从哪里来”和“AI 做了什么”能在创作界面中被连续观察。

## What Changes

- 在后端新增 AI 执行 trace 记录能力，用于记录灵感助手、未来 Agent、工具调用和管线步骤的结构化日志。
- 每条日志至少包含时间戳、会话/运行标识、步骤名称、步骤类别、输入参数摘要、输出摘要、状态、错误信息和参考的知识来源。
- 支持将 trace 暂存在内存或 SQLite 中，并提供前端可轮询或实时读取的接口；一期不要求长期归档或复杂检索。
- 为工具调用和管线步骤建立统一的 trace 写入边界，使 `create_card`、知识库检索、上下文装配、审核、生成等步骤能以一致方式被展示。
- 在创作界面右侧或底部新增“上下文洞察”面板，以时间线或步骤卡片展示 AI 执行痕迹。
- 面板需能把工具输入/输出 schema 转换成用户可理解的说明，例如“正在创建卡片：类型=对话，标题=...”、“已参考设定：[角色] 艾琳：性格傲娇，说话带刺”。
- 为 AI 输出文本预留来源高亮能力：当输出片段可关联到知识来源时，前端可高亮并在悬停时展示来源。
- 本次变更不要求暴露模型内部隐藏推理链，也不记录不可展示的私密推理内容；只记录系统可解释、可审计的工具、管线、上下文和知识引用事件。

## Capabilities

### New Capabilities

- `ai-execution-traces`: 为灵感助手、Agent、工具调用和管线步骤提供结构化执行日志、知识来源引用和前端上下文洞察展示能力。

### Modified Capabilities

- 无

## Impact

- 后端 AI 助手与工具执行：`backend/app/services/ai/assistant/`
- 后端工具管线与标准化事件：`backend/app/services/ai/core/`、未来 `tool-pipeline` 接入点
- 后端工作流/Agent 执行：`backend/app/services/workflow/`、`backend/app/api/endpoints/workflow_agent.py`
- 后端 trace schema、存储与 API：`backend/app/schemas/`、`backend/app/api/endpoints/`
- 前端创作界面与右侧/底部面板：`frontend/src/renderer/src/views/Editor.vue`、相关 panels/components
- 前端上下文可视化联动：`frontend/src/renderer/src/components/common/ContextDrawer.vue`、`frontend/src/renderer/src/services/contextVisualization.ts`
- 知识来源跳转：卡片、知识库、事实图谱和上下文来源引用展示链路
