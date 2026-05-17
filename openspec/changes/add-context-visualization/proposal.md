## Why

`NovelForge` 已经具备写作上下文装配、上下文模板解析和上下文抽屉入口，但当前呈现给用户的仍然主要是最终文本块，缺少“这段上下文从哪里来、被如何解析、最终怎样注入给模型”的可解释视图。结果是 AI 生成或审核一旦偏离预期，用户和开发者都很难快速判断问题出在模板、卡片引用、图谱事实，还是上下文截断。

在继续推进多 agent、工具规范化和知识库增强之前，先把上下文链路可视化，可以明显提升系统可控性、调试效率和用户心智清晰度。这一步能直接复用现有上下文接口与编辑器结构，属于高价值、低破坏面的演进。

## What Changes

- 在卡片编辑器的上下文抽屉中新增“上下文可视化”能力，展示模板、解析结果和最终注入内容三个层次。
- 为上下文装配结果增加可追踪的来源明细，使前端能够展示每个上下文片段的来源类型、来源对象、命中数量和截断信息。
- 为上下文模板解析结果增加结构化 token 视图，使用户可以识别 `facts.*`、`kg:*`、`$self/$parent/$current`、卡片引用等来源。
- 在上下文可视化中明确区分“原始模板”“解析后片段”“最终发送给模型的上下文文本”，用于排查生成偏差和提示词问题。
- 本次变更为增量能力，不改变现有生成接口契约，不引入新的模型调用链，不要求先完成多 agent 或知识库重构。

## Capabilities

### New Capabilities
- `context-visualization`: 为写作与审核场景提供上下文来源追踪、解析结果预览和最终注入预览的可视化工作台。

### Modified Capabilities
- 无

## Impact

- 后端上下文装配：`backend/app/services/context_service.py`
- 后端上下文接口：`backend/app/api/endpoints/context.py`
- 前端上下文模板解析：`frontend/src/renderer/src/services/contextResolver.ts`
- 前端上下文抽屉与卡片编辑器：`frontend/src/renderer/src/components/common/ContextDrawer.vue`
- 前端卡片编辑外壳：`frontend/src/renderer/src/components/cards/GenericCardEditor.vue`
- 前端上下文 API 类型：`frontend/src/renderer/src/api/ai.ts`
