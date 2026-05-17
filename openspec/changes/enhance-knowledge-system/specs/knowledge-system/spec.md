## ADDED Requirements

### Requirement: System SHALL support typed knowledge documents

The system SHALL support typed knowledge documents rather than a single undifferentiated knowledge entry model. At minimum, the system MUST support typed documents for `design`, `memory`, `skill`, and `reference`.

#### Scenario: Create a typed knowledge document
- **WHEN** 用户创建一条知识文档
- **THEN** 系统必须记录该文档的知识类型
- **AND** 类型必须属于受支持的知识类型集合

### Requirement: Knowledge documents SHALL define injection behavior

The system SHALL allow knowledge documents to define injection behavior for AI context usage.

#### Scenario: Knowledge document is marked for context injection
- **WHEN** 某条知识文档被配置为可注入
- **THEN** 系统必须保存其注入模式配置

#### Scenario: Knowledge document is excluded from injection
- **WHEN** 某条知识文档未启用注入
- **THEN** 系统不得默认将其加入 AI 上下文

### Requirement: System SHALL support summary-ready knowledge entries

The system SHALL support summary-ready knowledge entries so that long knowledge bodies can be represented in a shorter form for retrieval or injection.

#### Scenario: Long knowledge document requires summary
- **WHEN** 某条知识文档内容较长且启用了摘要能力
- **THEN** 系统必须允许该文档存在摘要表示

### Requirement: Knowledge system SHALL support retrieval by type and content

The system SHALL support retrieving knowledge documents by type and content-oriented query conditions.

#### Scenario: Filter by knowledge type
- **WHEN** 用户或系统按知识类型查询
- **THEN** 系统必须只返回匹配该类型的知识文档

#### Scenario: Search by query text
- **WHEN** 用户或系统提供查询文本
- **THEN** 系统必须能够返回与查询文本匹配的知识文档结果

### Requirement: Knowledge and memory SHALL remain distinct subsystems

The system SHALL preserve a distinction between long-lived knowledge documents and dynamic memory/graph facts.

#### Scenario: Dynamic relation fact is produced from chapter extraction
- **WHEN** 系统从章节中提取动态关系或状态事实
- **THEN** 该结果不得被强制写入知识文档系统作为同一类对象

#### Scenario: Stable writing rule is recorded
- **WHEN** 用户记录稳定的写作规则、设计文档或参考资料
- **THEN** 系统必须允许其作为知识文档保存，而不是要求写入 memory 图谱
