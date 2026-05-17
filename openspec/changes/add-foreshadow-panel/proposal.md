## Why

后端已经提供了伏笔登记、列出、回收、删除和候选建议接口，但前端只有 API 封装，没有任何实际入口或可见面板。结果是“伏笔”能力停留在半成品状态，用户无法在当前 GUI 中明确写入、查看和回收伏笔，功能价值无法兑现。

当前编辑器右侧已经存在章节相关侧栏能力（参与实体、提取、大纲、审核结果），伏笔面板与这一交互形态天然匹配。现在补齐该面板，可以直接复用既有后端能力，并把章节写作流程中的“埋设 -> 跟踪 -> 回收”闭环落到产品中。

## What Changes

- 在编辑器右侧侧栏新增 `伏笔` Tab，作为项目内伏笔登记的统一入口。
- 在伏笔面板中提供项目级伏笔列表，支持按 `open / resolved` 状态筛选和刷新。
- 提供手动登记能力，支持填写 `title`、`type`、`note`，并在当前激活卡片为章节正文时默认绑定 `chapter_id`。
- 提供条目动作能力，包括“标记已回收”、“删除”、“跳转到关联章节（若存在 chapter_id）”。
- 在当前激活卡片为章节正文时，提供基于当前章节文本的“候选建议”能力，并允许用户勾选后批量登记。
- 该变更为增量能力，不改变现有后端接口契约，不引入破坏性迁移。

## Capabilities

### New Capabilities
- `foreshadow-panel`: 为当前项目提供伏笔登记、查看、回收和候选建议的可视化工作台。

### Modified Capabilities
- 无

## Impact

- 前端编辑器侧栏：`frontend/src/renderer/src/views/Editor.vue`
- 前端新增面板组件：`frontend/src/renderer/src/components/panels/`
- 前端伏笔 API 调用复用：`frontend/src/renderer/src/api/ai.ts`
- 前端卡片导航与激活逻辑复用：`frontend/src/renderer/src/stores/useCardStore.ts`
- 后端接口复用，无需新增数据库表；MVP 直接使用现有 `/api/foreshadow/*` 接口
