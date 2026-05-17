## Context

当前系统已经有几条与本变更相关的基础链路：

- `tool-pipeline` 已提供统一工具定义、参数 schema、策略 metadata，以及 `tool_start` / `tool_end` 标准事件。
- 灵感助手和 workflow agent 已通过 SSE 把工具事件、token、reasoning 等流式事件传给前端。
- `Editor.vue` 右侧已有助手、参与实体、提取、伏笔、审核历史等面板，适合作为“上下文洞察”入口。
- `add-context-visualization` 已把“模板、解析、最终注入”做成上下文可视化方向，但它主要解释上下文文本，不覆盖工具执行、管线步骤和知识引用时间线。

本变更要补齐的是“AI 做了什么”的可观察层：记录可展示、可审计的工具调用、管线步骤、知识来源和输出摘要。它不能记录或暴露模型内部隐藏推理链；`reasoning` 流如果存在，也只作为模型供应商返回的可见事件处理，不能等同于系统必须保存的执行 trace。

## Goals / Non-Goals

**Goals:**

- 提供统一的 AI execution trace 数据模型，覆盖工具调用、管线步骤、知识检索、上下文装配、生成和审核等事件。
- 在后端提供 trace 写入服务、查询 API 和实时/近实时读取机制。
- 让现有 `tool_start` / `tool_end`、workflow agent、灵感助手和后续 Agent 编排都能复用同一 trace 记录入口。
- 在前端创作界面新增“上下文洞察”面板，用时间线或步骤卡片展示 trace。
- 将工具 schema、输入参数摘要、输出摘要和知识来源转换成用户可理解的文案。
- 为输出片段与知识来源的高亮关联预留数据结构。

**Non-Goals:**

- 不暴露模型隐藏 chain-of-thought 或不可展示的内部推理。
- 不在一期实现复杂的长期审计后台、全文检索或跨项目统计报表。
- 不强制把所有历史工具一次性迁移到 trace；一期优先接入统一工具管线和高价值创作路径。
- 不替代 `context-visualization`；本变更与其联动，但职责是执行时间线和知识引用。
- 不引入新的消息队列、外部日志平台或可观测性服务。

## Decisions

### 1. Trace 采用后端统一服务写入，而不是前端从 SSE 二次推断

后端新增 `ai_trace_service` 作为唯一写入入口，提供 `start_step`、`finish_step`、`fail_step`、`record_reference` 等最小 API。工具管线、Agent 流、上下文装配和生成管线只负责调用这个服务，不直接拼 UI 文案。

原因：

- 后端掌握工具参数、执行结果、错误、知识来源和权限边界，是 trace 的事实来源。
- 前端只从 SSE 推断会丢失失败步骤、后台步骤和非流式执行。
- 单一写入入口更容易统一脱敏、摘要、存储和运行标识。

备选方案：

- 只在前端消费 `tool_start` / `tool_end` 事件并本地显示：实现快，但不可回放，也覆盖不了非 SSE 步骤。
- 每个工具自行写日志：会重复 schema、脱敏和文案逻辑，长期难维护。

### 2. Trace 记录模型以“运行 run + 步骤 step + 来源 source”为核心

一期数据模型建议：

- `TraceRun`: `run_id`、`project_id`、`card_id`、`entrypoint`、`status`、`started_at`、`ended_at`
- `TraceStep`: `step_id`、`run_id`、`timestamp`、`name`、`kind`、`status`、`input_summary`、`output_summary`、`input_schema`、`output_schema`、`error`
- `TraceSource`: `source_id`、`step_id`、`source_type`、`source_ref`、`label`、`preview`、`jump_target`
- 可选 `TraceSpan`: `output_range`、`source_id`，用于未来输出片段高亮

`input_summary` 和 `output_summary` 是面向 UI 的摘要，不要求保存完整输入输出。完整参数可按安全策略保存结构化子集，默认过滤密钥、长正文和大对象。

备选方案：

- 保存完整 JSON 输入输出：调试信息最多，但更容易泄露正文、密钥或超大内容。
- 只保存一行自然语言日志：展示简单，但失去动态 UI 和来源跳转能力。

### 3. 存储采用可替换后端，一期默认 SQLite 或内存显式配置

提供 `TraceRepository` 接口，支持：

- SQLite repository：适合开发和本地应用持久查看。
- In-memory repository：适合快速迭代和测试，但进程重启即丢失。

存储模式必须显式配置，不做静默 fallback。若配置为 SQLite 但写入失败，应记录错误并让调用方能看到 trace 记录失败，不能伪造成功。

备选方案：

- 只用内存：实现最少，但用户刷新或重启后丢失，对调试价值有限。
- 直接复用通用日志文件：查询和前端结构化展示成本高。

### 4. 工具管线优先接入 `tool_start` / `tool_end` 事件

`build_tool_start_event` 和 `build_tool_end_event` 已经包含工具名、参数、结果、状态、策略信息，是最自然的接入点。设计上在流式 agent 执行层或工具管线 wrapper 中调用 trace 服务：

- start：创建 running step，记录工具名、参数摘要、schema 和 policy。
- end：更新 step 状态，记录输出摘要、错误、结构化来源。
- error：写入失败状态和错误信息。

工具本身如果知道知识来源，应通过标准字段返回，例如 `references`、`sources` 或 `knowledge_sources`，由 trace 服务归一化成 `TraceSource`。

备选方案：

- 在每个工具函数内部手写 trace：可控但重复。
- 只记录 agent 文本输出：不能解释工具和知识引用。

### 5. 前端面板消费 trace API，而不是直接耦合助手组件内部状态

新增 `InsightPanel` 或 `TraceInsightPanel`，挂到 `Editor.vue` 右侧 tabs，优先命名为“洞察”或“上下文洞察”。面板按 `project_id`、`card_id`、`run_id` 读取 trace：

- 当前运行中：通过 SSE trace 事件或定时轮询更新。
- 已完成运行：通过 REST 查询最后一次或最近 N 次 trace。

组件职责：

- 时间线/步骤卡片展示。
- 根据 `kind`、`name`、schema 和 source 元数据生成可读文案。
- 来源项可点击跳转卡片、知识库条目或图谱实体。
- 对可定位输出片段预留 hover source popover。

备选方案：

- 把 trace 列表塞进 `AssistantPanel`：实现近，但会让助手面板继续膨胀，也无法复用于生成、审核、工作流。
- 新建独立全屏工作台：更强，但一期入口过重。

### 6. 来源高亮作为数据契约预留，UI 一期可先展示来源列表

输出片段高亮需要模型输出、来源引用和文本范围之间有可靠映射。很多工具只能提供“参考了某来源”，不能精确到输出字符范围。因此一期数据结构预留 `TraceSpan`，但 UI 可以先展示来源卡片和可点击跳转；当步骤明确返回 span 时再启用高亮。

备选方案：

- 强制所有输出都做字符级引用：准确性要求过高，会让一期实现不稳定。
- 完全不设计 span：后续加高亮会破坏契约。

## Risks / Trade-offs

- [Risk] Trace 可能包含敏感输入、长正文或密钥。  
  → Mitigation：统一摘要和脱敏函数，默认不保存完整 prompt、正文和 secret-like 字段；需要完整 payload 时必须显式配置。

- [Risk] 每个 token 或细粒度事件都写入会造成 IO 压力。  
  → Mitigation：trace 只记录步骤级事件，流式 token 不逐条入库；输出摘要在步骤结束时写入。

- [Risk] 工具返回来源字段不统一，前端展示会不稳定。  
  → Mitigation：定义 `knowledge_sources` 标准字段，并在 trace 服务中兼容 `references` / `sources` 后归一化。

- [Risk] 用户可能把“执行 trace”误解为模型真实思维。  
  → Mitigation：UI 文案使用“执行步骤”“参考来源”“工具调用”，不使用“内心思考”或“真实推理链”等表述。

- [Risk] 与 `context-visualization` 产生职责重叠。  
  → Mitigation：上下文抽屉解释模板解析和最终注入；洞察面板解释运行过程、工具步骤和知识来源。

- [Risk] SQLite schema 过早固化会影响后续 Agent 扩展。  
  → Mitigation：核心字段稳定，扩展信息放入 `meta` JSON；新增字段通过迁移补充。

## Migration Plan

1. 定义 trace schema、repository 接口和内存/SQLite 实现。
2. 新增 trace API：创建/查询 run，查询 steps，按 project/card 获取最近 trace。
3. 在工具管线 wrapper 和 agent streaming 层写入 trace，不修改单个工具业务逻辑。
4. 为关键工具结果增加标准来源字段归一化，优先覆盖知识库检索、卡片搜索、创建/更新卡片、上下文装配。
5. 前端新增 trace API 类型和上下文洞察面板。
6. 将面板接入 `Editor.vue` 右侧 tabs，并让助手/生成/审核运行时传递或刷新当前 `run_id`。
7. 与 `context-visualization` 对齐来源展示语义，但不合并两个组件。

回滚策略：

- 前端可隐藏“上下文洞察”tab，不影响现有助手、生成和审核流程。
- 后端 trace 写入服务应与业务执行解耦；若 trace 写入失败，业务错误应明确区分，不能伪造 trace 成功。
- SQLite 存储若启用后需要回滚，可保留表数据但关闭 trace API 入口。

## Open Questions

- 一期默认存储应选择 SQLite 还是内存，是否按开发/生产配置区分？
- `run_id` 应由前端在发起助手/生成请求时创建，还是由后端入口自动创建并通过首个 SSE 事件返回？
- 知识来源跳转的统一格式是否直接复用现有 `AssistantRef`，还是新增 `TraceJumpTarget`？
- 输出高亮的首批支持范围是助手回复、章节正文生成，还是只做来源列表不做 span？
