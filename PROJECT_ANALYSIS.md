# NovelForge 项目原子分析

更新时间：2026-03-19

分析范围：
- 基于当前工作区静态源码、目录结构与 git 元信息
- 未启动前后端
- 未执行测试或构建

## 1. 项目定位

NovelForge 不是普通的 CRUD 应用，而是一个围绕小说创作构建的桌面优先 AI 创作平台。它的核心不是单点生成，而是把以下几类能力组合在一起：

- 项目与卡片树管理
- Schema-first 的结构化 AI 生成
- 灵感助手与工具调用
- 代码式工作流系统
- 关系图 / 记忆 / 知识库
- Electron 桌面壳与 Web 兼容渲染层

从仓库结构看，项目采用前后端同仓模式：

```text
NovelForge/
├── backend/   FastAPI + SQLModel + LangChain
├── frontend/  Electron + Vue 3 + Pinia
├── docImgs/   README 配图
├── rules/     规则与资源
└── README.md
```

参考：
- `backend/main.py`
- `backend/app/api/router.py`
- `frontend/src/main/index.ts`
- `frontend/src/renderer/src/main.ts`

## 2. Git 快照

静态分析时仓库状态：

- 当前分支：`main`
- 跟踪分支：`origin/main`
- 工作区存在本地修改：`.gitignore`
- 最近提交集中在 2026-03-14 到 2026-03-18，处于持续迭代中

结论：

- 这是活跃演进中的仓库
- 分析结论应视为当前快照，不应被当作长期不变的架构事实

## 3. 技术栈

### 3.1 后端

后端依赖核心：

- `fastapi`
- `uvicorn`
- `sqlmodel`
- `alembic`
- `pydantic`
- `langchain`
- `langchain-openai`
- `langchain-google-genai`
- `langchain-anthropic`
- `langchain_qwq`

参考：
- `backend/requirements.txt`

### 3.2 前端

前端核心依赖：

- Electron
- Vue 3
- Pinia
- Element Plus
- Axios
- CodeMirror
- Vue Flow
- `openapi-typescript`

参考：
- `frontend/package.json`

## 4. 顶层架构

项目可以拆成四层：

1. 产品域层
   - 项目、卡片、提示词、知识库、关系图、审核结果、伏笔等

2. AI 能力层
   - LLM 配置
   - 结构化生成
   - 助手 Agent
   - 指令流生成

3. 工作流平台层
   - 代码式 DSL
   - 节点注册
   - 校验器
   - 运行调度
   - 触发器
   - SSE 状态推送

4. 交互承载层
   - FastAPI API
   - Vue 渲染层
   - Electron 主进程 / preload

其中最像“平台内核”的部分有两个：

- `backend/app/services/workflow/`
- `backend/app/services/ai/`

## 5. 后端原子分析

### 5.1 启动链

后端入口在 `backend/main.py`。

启动顺序：

1. 加载邻近 `.env`
2. 创建 FastAPI 应用
3. 注册 `WorkflowHeaderMiddleware`
4. 注册 CORS
5. 挂载 API Router
6. 在 `lifespan` 中执行 `startup()`
7. 启动时额外清理过期工作流运行记录

参考：
- `backend/main.py`

### 5.2 启动初始化职责

`backend/app/core/startup.py` 不是简单的初始化脚本，而是后端装配中心。

它做了五件事：

1. `init_database()`
   - `SQLModel.metadata.create_all(engine)`
   - 自动补“安全新增列”

2. `init_application_data()`
   - 运行 bootstrap 初始化器

3. `register_event_handlers()`
   - 导入服务模块以触发事件注册

4. `register_workflow_nodes()`
   - 自动发现工作流节点

5. `cleanup_zombie_runs()`
   - 把上次异常终止后遗留的 `running` 任务改为 `failed`

这说明系统把“应用启动”视为“平台装配过程”，不是单纯起 Web 服务。

参考：
- `backend/app/core/startup.py`
- `backend/app/bootstrap/registry.py`

### 5.3 配置系统

统一配置在 `backend/app/core/config.py`。

关键点：

- 默认数据库为 SQLite
- 数据库路径支持环境变量覆盖
- 知识图谱 provider 可配置
- 兼容 Neo4j
- AI、工作流、应用配置集中收口到 `Settings`

这使得项目默认是“本地单机可跑”，但又保留图数据库和更复杂部署方式的扩展口。

参考：
- `backend/app/core/config.py`

### 5.4 数据模型中心

核心表都集中在 `backend/app/db/models.py`。

关键实体：

- `Project`
- `LLMConfig`
- `Prompt`
- `CardType`
- `Card`
- `Workflow`
- `WorkflowRun`
- `NodeExecutionState`
- `KGRelation`

它们构成了三个中心：

1. 创作中心
   - `Project`
   - `CardType`
   - `Card`

2. AI 配置中心
   - `LLMConfig`
   - `Prompt`

3. 自动化中心
   - `Workflow`
   - `WorkflowRun`
   - `NodeExecutionState`
   - `KGRelation`

其中 `Card` 是整个业务域的主轴：

- 属于 `Project`
- 关联 `CardType`
- 支持 `parent_id` 自引用形成树
- 内容采用 JSON 存储
- 支持实例级 schema 与 AI 参数覆盖

这意味着业务模型是“树形卡片文档系统”，不是扁平表单系统。

参考：
- `backend/app/db/models.py`

### 5.5 API 分层

总路由在 `backend/app/api/router.py`。

主要 API 域：

- `/projects`
- `/llm-configs`
- `/ai`
- `/prompts`
- `/cards`
- `/chapter-reviews`
- `/context`
- `/memory`
- `/relation-graph`
- `/foreshadow`
- `/knowledge`
- `/workflows`
- `/workflow-agent`

这说明后端边界是按领域拆分的，而不是单一“大服务入口”。

参考：
- `backend/app/api/router.py`

### 5.6 AI 生成链

AI 生成核心入口在 `backend/app/api/endpoints/ai.py`。

标准结构化生成流程：

1. 读取 prompt
2. 注入知识库
3. 构造 system prompt
4. 注入 JSON Schema
5. 调用 `llm_service.generate_structured`

底层在 `backend/app/services/ai/core/llm_service.py`：

- 调用 `build_chat_model()`
- 构造 LangChain model
- 使用 `with_structured_output(output_type)`
- 输出 Pydantic 结构对象

这是一条典型的 Schema-first 生成链，说明项目追求的是“结构正确”优先，而不是自由文本优先。

参考：
- `backend/app/api/endpoints/ai.py`
- `backend/app/services/ai/core/llm_service.py`
- `backend/app/services/ai/core/chat_model_factory.py`

### 5.7 LLM 提供商适配

模型工厂位于 `backend/app/services/ai/core/chat_model_factory.py`。

已适配：

- OpenAI
- OpenAI compatible
- Anthropic
- Google

并显式建模了：

- `chat_completions`
- `responses`

这块设计的优点是 provider 差异集中在一个工厂里，不把参数拼装逻辑散落到业务代码中。

参考：
- `backend/app/services/ai/core/chat_model_factory.py`
- `backend/app/services/llm_config_service.py`

### 5.8 助手系统

助手核心在 `backend/app/services/ai/assistant/assistant_service.py`。

内部存在两套路径：

- `stream_chat_with_react_protocol`
- `stream_agent_with_tools`

共用：

- 配额预检 `precheck_quota`
- 用量记录 `record_usage`
- `AssistantDeps`

这说明作者区分了：

- 纯对话式助手
- 工具可行动助手

这种分层是合理的，因为两者在模型要求、可控性和 token 消耗上都不同。

参考：
- `backend/app/services/ai/assistant/assistant_service.py`

### 5.9 工作流平台

工作流模块是整个仓库最复杂的后端子系统。

#### 注册机制

节点通过 `@register_node` 装饰器注册到全局注册表：

- `backend/app/services/workflow/registry.py`

#### 运行时

运行管理器在：

- `backend/app/services/workflow/engine/run_manager.py`

主要职责：

1. 创建 `WorkflowRun`
2. 清理旧节点状态
3. 调度执行协程
4. 解析 DSL
5. 构建初始上下文
6. 交给 `AsyncExecutor` 流式执行

#### 触发器

触发器在：

- `backend/app/services/workflow/triggers.py`

特点：

- 使用事件系统触发
- 有 `_DEBOUNCE_MS = 1500` 去抖
- 为运行生成 `idempotency_key`

#### 校验器

校验器在：

- `backend/app/services/workflow/validator.py`

这是后端最大热点之一，说明 DSL 语义检查已经比较重。

总结：

工作流系统不是装饰性功能，而是独立平台层，具备：

- 代码式 DSL
- 节点元数据系统
- 执行引擎
- 触发器
- 状态恢复
- SSE 推送

参考：
- `backend/app/services/workflow/__init__.py`
- `backend/app/services/workflow/registry.py`
- `backend/app/services/workflow/engine/run_manager.py`
- `backend/app/services/workflow/triggers.py`
- `backend/app/services/workflow/validator.py`

## 6. 前端原子分析

### 6.1 渲染层入口

渲染层入口在 `frontend/src/renderer/src/main.ts`。

启动顺序：

1. 执行 `setupWebMock()`
2. 创建 Vue 应用
3. 注入 Pinia
4. 注入 Element Plus
5. 初始化主题
6. 加载卡片级 AI 设置缓存
7. 挂载 `App.vue`

这说明 renderer 被设计成可在 Electron 和 Web 两种环境中共用。

参考：
- `frontend/src/renderer/src/main.ts`
- `frontend/src/renderer/src/web-mock.ts`

### 6.2 顶层视图控制

顶层视图不主要依赖 `vue-router`，而是用 `useAppStore` 管理：

- `dashboard`
- `editor`
- `ideas`
- `workflows`
- `code-workflows`
- `triggers`

`App.vue` 根据 `currentView` 选择渲染哪个主视图，再通过 `hash` 与特殊页面同步。

这属于“轻路由 + 状态驱动页面切换”方案。

参考：
- `frontend/src/renderer/src/App.vue`
- `frontend/src/renderer/src/stores/useAppStore.ts`

### 6.3 Electron 主进程

Electron 主进程在 `frontend/src/main/index.ts`。

职责并不重，主要是：

- 创建主窗口
- 打开灵感工作台窗口
- 设置 CSP
- 暴露 keytar 密钥接口
- 暴露打开灵感页接口

preload 只桥接了三个方法：

- `setApiKey`
- `getApiKey`
- `openIdeasHome`

说明当前桌面壳比较薄，主要价值在：

- 原生窗口
- 本机安全存储能力

参考：
- `frontend/src/main/index.ts`
- `frontend/src/preload/index.ts`

### 6.4 API 请求层

请求基座在 `frontend/src/renderer/src/api/request.ts`。

它统一处理：

- `BASE_URL`
- Electron / Web 环境差异
- loading 遮罩
- 标准响应解包
- 422 错误提示
- 透传原始响应
- 读取 `X-Workflows-Started` 并派发全局事件

这层做得比较完整，说明前端已有明显的 API 基础设施意识。

参考：
- `frontend/src/renderer/src/api/request.ts`

### 6.5 Store 分工

#### `useProjectStore`

职责很薄：

- 当前项目
- 加载状态
- 自由项目加载

参考：
- `frontend/src/renderer/src/stores/useProjectStore.ts`

#### `useCardStore`

这是前端重逻辑中心之一。

职责包括：

- 监听项目切换自动加载卡片
- 卡片树构建
- 卡片增删改
- 更新后读取 `X-Workflows-Started`
- 打开 SSE 订阅工作流结果
- SSE 失败时降级到轮询
- 合并局部刷新结果

这说明 `useCardStore` 已经不是纯状态容器，而是“状态 + 协议编排 + 增量刷新”的复合层。

参考：
- `frontend/src/renderer/src/stores/useCardStore.ts`
- `frontend/src/renderer/src/api/cards.ts`

#### `useAssistantStore`

这是前端另一个重型 store。

职责包括：

- 引用卡片管理
- 章节摘录引用
- 审核结果引用
- 对话历史持久化
- 项目结构文本构建
- 最近操作记录
- localStorage 缓存

它实际充当了“助手上下文中台”。

参考：
- `frontend/src/renderer/src/stores/useAssistantStore.ts`

#### `useWorkflowStore`

主要负责：

- 节点类型元数据
- 工作流运行列表
- SSE 连接管理
- 恢复执行

参考：
- `frontend/src/renderer/src/stores/useWorkflowStore.ts`

### 6.6 LLM 配置前端流

LLM 配置表单在：

- `frontend/src/renderer/src/components/setting/LLMConfigForm.vue`

接口层在：

- `frontend/src/renderer/src/api/setting.ts`

表单直接处理：

- `api_key`
- 获取模型列表
- 测试连接
- 创建 / 更新配置

这块前端流是直接把密钥送给后端 API 的。

## 7. 关键调用链

### 7.1 项目创建链

调用链：

1. 前端创建项目
2. 请求 `POST /projects/`
3. `project_service.create_project(...)`
4. 中间件根据触发结果把工作流运行 ID 写入 header

参考：
- `frontend/src/renderer/src/api/projects.ts`
- `backend/app/api/endpoints/projects.py`

### 7.2 卡片保存触发工作流链

调用链：

1. 前端更新卡片
2. `PUT /cards/{id}`
3. 响应头返回 `X-Workflows-Started`
4. 前端 `useCardStore` 读取 header
5. 前端打开 SSE 监听运行状态
6. 完成后刷新受影响卡片或全量刷新

参考：
- `frontend/src/renderer/src/api/cards.ts`
- `frontend/src/renderer/src/stores/useCardStore.ts`
- `backend/app/core/middleware/workflow.py`
- `backend/app/api/endpoints/cards.py`

### 7.3 结构化 AI 生成链

调用链：

1. 前端发起 `/ai/generate`
2. 后端读取 prompt
3. 注入知识库
4. 拼接 schema 到 system prompt
5. `llm_service.generate_structured`
6. `build_chat_model`
7. LangChain `with_structured_output`
8. 返回结构化 JSON

参考：
- `frontend/src/renderer/src/api/ai.ts`
- `backend/app/api/endpoints/ai.py`
- `backend/app/services/ai/core/llm_service.py`
- `backend/app/services/ai/core/chat_model_factory.py`

### 7.4 工作流执行链

调用链：

1. 创建 `WorkflowRun`
2. 调度 `RunManager.start_run`
3. 解析 DSL
4. 构造执行计划
5. `AsyncExecutor` 执行节点
6. 节点状态写入 `NodeExecutionState`
7. SSE 将运行状态推送前端

参考：
- `backend/app/services/workflow/engine/run_manager.py`
- `backend/app/services/workflow/engine/async_executor.py`
- `backend/app/api/endpoints/workflows.py`

## 8. 架构优点

### 8.1 领域模型清晰

项目、卡片、卡片类型、提示词、工作流、运行记录、关系图这些核心对象边界相对明确，业务主轴比较稳定。

### 8.2 AI 能力不是硬编码在页面里

LLM 配置、Prompt、Schema、知识注入、工具助手都在后端服务层收口，前端主要负责配置和交互。

### 8.3 工作流系统具备平台化雏形

这不是简单脚本执行器，而是具备注册、校验、触发、调度、状态持久化和恢复能力的执行平台。

### 8.4 前后端类型联动较好

前端通过 OpenAPI 生成类型，降低了接口漂移风险。

## 9. 主要风险与技术债

### 9.1 LLM 密钥设计前后不一致

这是当前最明显的架构矛盾。

现状：

- Electron 主进程提供了 keytar 安全存储能力
- 但前端配置表单并没有把密钥主路径迁移到 keytar
- 后端 `LLMConfig` 仍直接持久化 `api_key`
- `LLMConfigRead` 也直接包含 `api_key`

结果：

- “安全存储”存在，但没有成为主路径
- 当前真实行为更接近“数据库明文持久化 + API 回传”

相关位置：

- `frontend/src/main/index.ts`
- `frontend/src/preload/index.ts`
- `frontend/src/renderer/src/components/setting/LLMConfigForm.vue`
- `backend/app/db/models.py`
- `backend/app/schemas/llm_config.py`

### 9.2 数据库迁移策略双轨

系统同时依赖：

- Alembic
- 启动时 `create_all`
- 启动时自动补安全新增列

这在开发期便利，但会让 schema 演进来源变成：

- 迁移脚本
- 模型代码
- 启动副作用

长期维护容易产生认知分裂。

相关位置：

- `backend/requirements.txt`
- `backend/app/core/startup.py`
- `backend/alembic/`

### 9.3 大文件热点严重

按行数看，已经有多个热点远超项目自己的硬限制。

重点热点：

- `backend/app/services/workflow/validator.py`
- `backend/app/api/endpoints/workflows.py`
- `backend/app/services/ai/assistant/tools.py`
- `frontend/src/renderer/src/views/Editor.vue`
- `frontend/src/renderer/src/components/workflow/editor/NodeBlockEditor.vue`
- `frontend/src/renderer/src/components/cards/GenericCardEditor.vue`

这类文件通常意味着：

- 职责耦合
- 修改成本高
- 回归风险大

### 9.4 前端 store 跨层

`useCardStore` 和 `useAssistantStore` 都在承担超出“状态管理”的职责。

表现：

- 直接处理协议细节
- 管 SSE 生命周期
- 做本地缓存策略
- 做结构文本构建
- 做局部数据合并

这会让前端状态层逐渐演化为“隐式服务层”。

### 9.5 Web Mock 与 Debug-First 存在冲突

`web-mock.ts` 中部分 Electron 能力被 mock 成成功返回。

这意味着在缺失桌面能力时，前端可能得到“看似成功”的结果，而不是显式失败。

这与项目强调的“不做静默 fallback”并不完全一致。

相关位置：

- `frontend/src/renderer/src/web-mock.ts`

### 9.6 自动化验证偏弱

当前能明确看到的工程脚本主要是：

- 前端 `lint`
- 前端 `typecheck`
- 前端 `build`
- 根目录一键 `dev`

但没有看到成体系的：

- 后端单元测试脚本
- 前端单元测试脚本
- E2E 测试脚本

这意味着当前质量更多依赖：

- 类型检查
- 运行时报错
- 人工验证

## 10. 热点文件清单

静态扫描中最明显的大文件：

- `frontend/src/renderer/src/types/generated.d.ts`
- `frontend/src/renderer/src/components/editors/CodeMirrorEditor.vue`
- `frontend/src/renderer/src/components/workflow/editor/NodeBlockEditor.vue`
- `frontend/src/renderer/src/views/Editor.vue`
- `backend/app/services/workflow/validator.py`
- `frontend/src/renderer/src/components/cards/GenericCardEditor.vue`
- `frontend/src/renderer/src/components/workflow/Workflow.vue`
- `backend/app/services/ai/assistant/tools.py`
- `frontend/src/renderer/src/components/assistants/AssistantPanel.vue`
- `backend/app/api/endpoints/workflows.py`

说明：

- 真正的复杂度热点集中在工作流编辑器、主编辑器、工作流校验器、助手工具层
- 这与项目的产品复杂度是吻合的

## 11. 结论

对当前仓库的判断如下：

- 这已经不是 demo 项目，而是有明确产品域和平台层的中型应用
- 后端最核心的价值在工作流平台和 Schema-first AI 生成
- 前端最核心的价值在编辑器交互、卡片上下文、工作流可视化和状态编排
- 当前最大的工程风险不是“功能缺失”，而是“复杂度增长快于模块边界治理”

一句话总结：

> NovelForge 已经具备平台化创作系统的骨架，但密钥边界、迁移策略、大文件治理和前端职责收敛仍是当前最值得优先关注的工程问题。

## 12. 主要参考文件

- `backend/main.py`
- `backend/app/core/startup.py`
- `backend/app/core/config.py`
- `backend/app/api/router.py`
- `backend/app/api/endpoints/ai.py`
- `backend/app/api/endpoints/cards.py`
- `backend/app/api/endpoints/projects.py`
- `backend/app/api/endpoints/workflows.py`
- `backend/app/db/models.py`
- `backend/app/services/ai/core/llm_service.py`
- `backend/app/services/ai/core/chat_model_factory.py`
- `backend/app/services/ai/assistant/assistant_service.py`
- `backend/app/services/llm_config_service.py`
- `backend/app/services/workflow/registry.py`
- `backend/app/services/workflow/engine/run_manager.py`
- `backend/app/services/workflow/triggers.py`
- `backend/app/services/workflow/validator.py`
- `frontend/src/main/index.ts`
- `frontend/src/preload/index.ts`
- `frontend/src/renderer/src/main.ts`
- `frontend/src/renderer/src/App.vue`
- `frontend/src/renderer/src/api/request.ts`
- `frontend/src/renderer/src/api/cards.ts`
- `frontend/src/renderer/src/api/ai.ts`
- `frontend/src/renderer/src/stores/useAppStore.ts`
- `frontend/src/renderer/src/stores/useProjectStore.ts`
- `frontend/src/renderer/src/stores/useCardStore.ts`
- `frontend/src/renderer/src/stores/useAssistantStore.ts`
- `frontend/src/renderer/src/stores/useWorkflowStore.ts`
- `frontend/src/renderer/src/components/setting/LLMConfigForm.vue`
