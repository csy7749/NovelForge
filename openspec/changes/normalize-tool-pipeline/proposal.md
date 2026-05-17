## Why

`NovelForge` 当前已经有一批真实可执行的 AI 工具，但工具定义、参数契约、权限边界和执行事件还比较分散，主要体现在 `assistant/tools.py` 等模块中。随着后续要接入多 agent、上下文可视化和知识片段注入，若工具仍保持“分散注册、各自返回格式、权限靠提示词约定”的状态，系统会越来越难维护。

把工具能力拆成独立 change，可以先把“工具是什么、怎么注册、谁能调、怎么回传结果”做成统一管线。这是后续多 agent 和更复杂助手形态的底层前提。

## What Changes

- 建立统一的工具定义模型，涵盖名称、参数 schema、执行器、权限/确认策略和结果格式。
- 统一 AI 工具注册与解析方式，替代散落在各服务中的临时注册模式。
- 为工具调用增加标准化事件流和结果结构，便于前端展示和日志追踪。
- 为不同 agent 或入口增加可配置工具白名单/能力范围。
- 本次变更为基础设施改造，不要求一次重写所有工具实现，但要求定义统一接入标准。

## Capabilities

### New Capabilities
- `tool-pipeline`: 为 AI 工具提供统一的定义、注册、授权、执行和结果回传管线。

### Modified Capabilities
- 无

## Impact

- 后端助手工具：`backend/app/services/ai/assistant/tools.py`
- 后端 AI 核心执行流：`backend/app/services/ai/core/`
- 工具结果协议：`backend/app/schemas/`
- 前端工具调用展示链路：AI/assistant 相关组件和事件流消费逻辑
