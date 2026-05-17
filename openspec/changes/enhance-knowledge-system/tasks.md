## 1. OpenSpec 对齐

- [x] 1.1 确认 `knowledge-system` capability 的 proposal、design、spec 内容与当前 knowledge/memory 现状一致
- [x] 1.2 使用 OpenSpec 校验 `enhance-knowledge-system` 变更文档

## 2. 知识模型设计

- [x] 2.1 梳理当前 knowledge、memory、bootstrap 知识和上下文装配的边界
- [x] 2.2 设计 typed knowledge document 模型，覆盖类型、注入模式、摘要与维护字段
- [x] 2.3 明确 knowledge 与 memory 的职责分工和协作接口

## 3. 后端能力增强

- [x] 3.1 扩展知识存储与接口，支持类型字段和注入配置
- [x] 3.2 增加知识摘要表示与基础检索能力
- [x] 3.3 保持旧 knowledge CRUD 的兼容路径

## 4. 注入与消费链路接入

- [x] 4.1 为 AI 上下文注入链路设计知识文档选择与注入策略
- [x] 4.2 为前端知识管理入口补充类型与检索视图所需数据
- [x] 4.3 为后续语义检索预留扩展接口而不强行落地完整实现

## 5. 验证

- [x] 5.1 验证 typed knowledge document 的创建、更新、查询与注入配置
- [x] 5.2 验证 knowledge 与 memory 两条路径不会相互覆盖或混淆
