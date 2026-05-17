# Findings

- `enhance-knowledge-system` 使用 `spec-driven` schema，共 13 个任务，初始进度 0/13。
- OpenSpec 要求至少支持 `design`、`memory`、`skill`、`reference` 四类 typed knowledge document。
- 知识文档需要保存注入行为；未启用注入的文档不得默认进入 AI 上下文。
- 知识文档需要摘要表示，支持按类型和文本条件检索。
- `knowledge` 与 `memory` 必须保持边界：memory 负责动态事实/关系/故事状态，knowledge 负责稳定设计文档、参考资料、技能说明和长期规则。
- 当前 `Knowledge` 模型只有 `name/description/content/built_in`，API 和前端均按简单 CRUD 使用。
- `prompt_service.inject_knowledge` 通过显式 `@KB{id=...}` / `@KB{name=...}` 占位符注入全文，这是需要保留的旧兼容路径。
- `context_service` 和 `continuation_context_service` 当前只处理 memory/图谱事实；knowledge 自动注入尚未接入。
- 启动期 `_ensure_safe_additive_columns` 可自动补齐安全新增列，因此新增 knowledge 可空列或带 server_default 的非空列可兼容旧库。
- 新实现保留显式 `@KB{...}` 旧占位符全文注入；空 `- knowledge:` 段会追加启用注入的知识文档。
- 语义检索作为 `retrieval_backend=semantic` 预留接口存在，但当前会显式报错，不会伪装成关键词检索。
