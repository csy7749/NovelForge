## ADDED Requirements

### Requirement: Context drawer SHALL expose template, resolution, and injection views

The system SHALL provide a context visualization workspace inside the existing context drawer for card editing flows. The workspace MUST expose three distinct views: original template, resolved context fragments, and final injected context text.

#### Scenario: Open context drawer for a card with context template
- **WHEN** 用户在卡片编辑器中打开上下文抽屉
- **THEN** 系统必须提供“模板视图”“解析视图”“最终注入视图”三类可切换内容
- **AND** 这些视图必须基于当前激活卡片与当前选中的上下文模板类型生成

#### Scenario: Card has no usable context template
- **WHEN** 当前卡片没有可用的上下文模板
- **THEN** 系统必须展示明确的空状态说明
- **AND** 不得伪造上下文可视化结果

### Requirement: System SHALL show structured resolution results with source attribution

The system SHALL present resolved context fragments as structured results with explicit source attribution. Each fragment MUST identify its source kind, readable label, and preview content, and MUST indicate whether the fragment was truncated when such information is available.

#### Scenario: Resolved fragment comes from a card reference
- **WHEN** 模板命中某张卡片或某个卡片字段
- **THEN** 解析视图必须展示该片段的来源类别为卡片引用
- **AND** 必须展示可识别的来源对象信息，例如卡片标题、字段路径或卡片 id

#### Scenario: Resolved fragment comes from facts or entity summaries
- **WHEN** 模板命中 `facts.*`、`kg:*`、物品摘要或概念摘要
- **THEN** 解析视图必须将这些结果展示为结构化来源项
- **AND** 每个来源项必须包含至少一个可阅读的预览内容

#### Scenario: Fragment is truncated during context assembly
- **WHEN** 某个上下文片段在装配过程中被截断
- **THEN** 解析视图必须显式标识该片段已截断

### Requirement: System SHALL expose the final model-visible context text

The system SHALL display the final injected context text exactly as assembled for model consumption. This view MUST allow users to verify what the model will actually receive after template resolution and formatting.

#### Scenario: Final context is available
- **WHEN** 上下文装配成功
- **THEN** 最终注入视图必须展示实际将发送给模型的上下文文本
- **AND** 该文本必须与当前装配结果一致，不得使用单独重算的副本

#### Scenario: Assembly result differs from resolved fragments due to formatting
- **WHEN** 最终上下文文本经过分段、拼接或截断处理
- **THEN** 系统仍必须展示最终模型可见文本
- **AND** 用户必须能够区分它与解析视图中的结构化来源项

### Requirement: Context assembly API SHALL return visualization trace metadata

The context assembly response SHALL include optional trace metadata sufficient to power source-aware visualization. The trace metadata MUST be additive and MUST NOT remove or replace existing context response fields required by current clients.

#### Scenario: Existing client consumes context assembly response
- **WHEN** 旧客户端仍仅读取现有 `facts_subgraph` 或 `facts_structured`
- **THEN** 新增的可视化 trace 字段不得破坏原有响应契约

#### Scenario: Visualization client requests context details
- **WHEN** 前端上下文可视化读取装配结果
- **THEN** 响应中必须包含可用于展示来源类别、来源对象、预览内容、命中数量或截断状态的 trace 元数据

### Requirement: Visualization SHALL surface missing or failed context resolution explicitly

The system SHALL explicitly surface missing sources, unresolved tokens, or context assembly failures in the visualization UI. It MUST NOT silently replace them with fabricated success states.

#### Scenario: Template token cannot be resolved
- **WHEN** 某个模板 token 无法命中任何有效来源
- **THEN** 解析视图必须明确标识该 token 未解析成功
- **AND** 不得伪造默认内容掩盖问题

#### Scenario: Context assembly fails for the current card
- **WHEN** 当前卡片上下文装配失败
- **THEN** 上下文可视化必须展示错误状态
- **AND** 错误状态必须阻止用户误以为模型已经获得完整上下文
