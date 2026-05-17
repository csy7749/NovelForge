## ADDED Requirements

### Requirement: System SHALL support explicit agent roles for AI task execution

The system SHALL support explicit agent role definitions for AI task execution. Each agent role MUST define its responsibility boundary and MUST be distinguishable from other agents by purpose, not only by prompt text.

#### Scenario: Register a specialist agent
- **WHEN** 系统新增一个专职 agent
- **THEN** 该 agent 必须具备明确职责标识
- **AND** 不得仅通过模糊提示词约定其用途

### Requirement: Primary agent SHALL be able to delegate tasks to specialist agents

The system SHALL allow a primary agent to delegate bounded tasks to specialist agents and collect their results. Delegation MUST preserve the task boundary and MUST identify which agent produced the returned result.

#### Scenario: Delegate a review task
- **WHEN** 主 agent 判断当前请求属于审校类任务
- **THEN** 系统必须能够将该任务委派给审校专职 agent
- **AND** 返回结果必须标识由审校 agent 产出

#### Scenario: Delegate an extraction task
- **WHEN** 主 agent 判断当前请求属于关系或记忆抽取类任务
- **THEN** 系统必须能够将该任务委派给相应专职 agent

### Requirement: Each agent SHALL have an explicit allowed tool scope

The system SHALL define an explicit allowed tool scope for each agent. An agent MUST NOT invoke tools outside its configured scope.

#### Scenario: Specialist agent receives restricted tool set
- **WHEN** 某个专职 agent 被配置为只允许使用部分工具
- **THEN** 系统必须只向该 agent 暴露被允许的工具集合

#### Scenario: Agent attempts to use disallowed tool
- **WHEN** agent 尝试调用未授权工具
- **THEN** 系统必须阻止该调用
- **AND** 必须显式记录该失败，而不是静默降级

### Requirement: Delegation SHALL use structured task and result contracts

The system SHALL use structured task and result contracts for agent delegation. Free-form delegation without task typing or result identification MUST NOT be the only supported path.

#### Scenario: Create delegated task payload
- **WHEN** 主 agent 发起委派
- **THEN** 系统必须生成结构化任务载荷
- **AND** 该载荷必须至少包含任务类型、目标 agent 和任务内容

#### Scenario: Receive delegated result
- **WHEN** 子 agent 完成任务
- **THEN** 系统必须返回结构化结果
- **AND** 结果中必须包含来源 agent 与结果内容

### Requirement: Multi-agent execution SHALL remain compatible with existing single-agent flows

The system SHALL allow staged adoption of multi-agent execution. Existing single-agent flows MUST continue to function when multi-agent routing is not enabled for a given request path.

#### Scenario: Route is not migrated to multi-agent
- **WHEN** 某个现有 AI 入口尚未启用多 agent 路由
- **THEN** 系统必须继续支持原有单 agent 执行方式
