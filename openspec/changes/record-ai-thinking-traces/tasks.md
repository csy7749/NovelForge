## 1. OpenSpec 对齐

- [x] 1.1 确认 `ai-execution-traces` proposal、design、spec 与现有助手、工具管线、上下文可视化边界一致
- [x] 1.2 使用 OpenSpec 严格校验 `record-ai-thinking-traces` 变更文档

## 2. 后端 Trace 数据模型与存储

- [x] 2.1 定义 trace run、step、source、span 的 Pydantic schema，覆盖时间戳、步骤名、输入摘要、输出摘要、错误和知识来源字段
- [x] 2.2 设计 `TraceRepository` 接口，并实现显式配置的 in-memory repository
- [x] 2.3 实现 SQLite repository 或本地持久化路径，确保写入失败显式报错且不静默降级
- [x] 2.4 实现输入/输出摘要与脱敏工具，过滤密钥、长正文和超大对象
- [x] 2.5 实现知识来源归一化逻辑，兼容 `knowledge_sources`、`sources`、`references`

## 3. 后端 Trace 服务与 API

- [x] 3.1 新增 `ai_trace_service`，提供创建 run、开始 step、完成 step、失败 step、记录 source 的统一入口
- [x] 3.2 新增 trace API，支持按 project、card、run 查询最近 trace runs 和 ordered steps
- [x] 3.3 为 active run 提供可轮询或 SSE 可关联的 run id 输出机制
- [x] 3.4 将 trace API 注册到后端 router，并补充响应模型确保前端类型可生成

## 4. 工具管线与执行链路接入

- [x] 4.1 在 `tool_pipeline` 或 agent streaming 层接入 `tool_start` / `tool_end` 到 trace step 的转换
- [x] 4.2 为 React 文本 agent 工具调用路径记录 trace step，覆盖成功和失败状态
- [x] 4.3 为 LangGraph/tool agent streaming 路径记录 trace step，保留 tool call id 关联
- [x] 4.4 为生成、审核、上下文装配等非工具管线步骤记录基础 trace step
- [x] 4.5 确认 trace 写入失败与业务执行失败有明确区分，不伪造成功状态

## 5. 前端 API 与视图模型

- [x] 5.1 新增前端 trace API 类型与请求函数，接入后端 trace run/step/source 响应
- [x] 5.2 提炼前端 trace 视图模型，将 tool schema、输入摘要、输出摘要转换为用户可读步骤卡片
- [x] 5.3 实现来源跳转模型，支持卡片、知识库条目、图谱实体等 jump target
- [x] 5.4 为缺失来源、失败步骤、运行中步骤提供明确 UI 状态

## 6. 上下文洞察面板

- [x] 6.1 新增 `TraceInsightPanel` 或同等组件，以时间线/步骤卡片展示 trace
- [x] 6.2 将上下文洞察面板接入 `Editor.vue` 右侧或底部创作界面
- [x] 6.3 支持根据当前 project/card/run 加载最近 trace，并在 active run 中轮询或实时刷新
- [x] 6.4 展示工具调用、管线步骤、知识来源、错误和状态标签
- [x] 6.5 支持点击来源跳转到对应卡片、知识条目或图谱实体

## 7. 输出来源高亮预留

- [x] 7.1 在后端 trace schema 中保留 output span 与 source 的关联结构
- [x] 7.2 在前端视图模型中保留 span 到 source 的映射能力
- [x] 7.3 在有 span 数据时支持输出文本 hover 展示来源；无 span 时只展示来源列表且不伪造高亮

## 8. 验证与回归

- [x] 8.1 验证 `create_card`、卡片搜索、知识/上下文引用等典型工具调用会生成 trace
- [x] 8.2 验证工具失败、存储失败、来源缺失场景会显式展示错误或空状态
- [x] 8.3 验证上下文洞察面板不会暴露隐藏模型推理链或不可展示的内部 reasoning
- [x] 8.4 运行后端目标测试或接口级验证，确认 trace API 可用
- [x] 8.5 运行前端类型检查与必要 UI 回归，确认现有助手、上下文面板、生成和审核流程未被破坏
