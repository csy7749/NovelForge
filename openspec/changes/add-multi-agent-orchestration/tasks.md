## 1. OpenSpec 对齐

- [x] 1.1 确认 `multi-agent-orchestration` capability 的 proposal、design、spec 内容与当前 AI 架构一致
- [x] 1.2 使用 OpenSpec 校验 `add-multi-agent-orchestration` 变更文档

## 2. Agent 模型与注册

- [x] 2.1 盘点当前已有的助手、抽取器和工作流 AI 角色，确定一期 agent 切分边界
- [x] 2.2 设计 agent 配置模型，覆盖职责、工具白名单、默认上下文策略和路由标识
- [x] 2.3 实现 agent 注册与查询机制，支持主 agent 与专职 agent 装配

## 3. 委派协议与执行流

- [x] 3.1 设计结构化 task/result 协议，明确委派载荷与回传格式
- [x] 3.2 在现有 AI core 上实现主 agent 到专职 agent 的委派执行流
- [x] 3.3 为委派结果增加来源 agent 标识与执行状态记录
- [x] 3.4 为未授权工具调用和子 agent 失败添加显式错误路径

## 4. 一期场景接入

- [x] 4.1 为写作助手接入多 agent 路由的最小路径
- [x] 4.2 为关系/记忆抽取场景接入专职 agent
- [x] 4.3 为审校场景接入专职 agent
- [x] 4.4 保持未迁移入口继续走单 agent 流程

## 5. 验证

- [x] 5.1 验证委派、回传、工具授权和失败暴露链路
- [x] 5.2 验证单 agent 兼容路径未被破坏
