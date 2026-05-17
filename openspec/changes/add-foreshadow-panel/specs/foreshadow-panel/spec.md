## ADDED Requirements

### Requirement: Editor SHALL expose a foreshadow panel for the active project

The system SHALL provide a sidebar entry named "伏笔" in the editor. 只要用户当前处于项目编辑器并激活了卡片，该面板就必须可访问，并且必须基于当前项目加载伏笔数据。

#### Scenario: Active card is selected in editor
- **WHEN** 用户在项目编辑器中选中任意卡片
- **THEN** 右侧侧栏必须包含“伏笔”Tab
- **AND** 该面板必须使用当前项目 id 作为伏笔查询范围

#### Scenario: No active card is selected
- **WHEN** 编辑器中没有激活卡片
- **THEN** 系统不得展示可操作的伏笔面板内容

### Requirement: Users SHALL be able to view and filter foreshadow items

The system SHALL allow users to view foreshadow items for the current project and filter them by status. 列表项必须展示足以识别条目的核心信息，至少包括标题、类型、状态、创建时间和备注摘要。

#### Scenario: View open foreshadow items
- **WHEN** 用户打开伏笔面板且当前筛选状态为 `open`
- **THEN** 系统必须请求并展示当前项目下所有未回收伏笔

#### Scenario: Switch filter to resolved
- **WHEN** 用户将筛选状态切换为 `resolved`
- **THEN** 系统必须刷新列表并仅展示已回收伏笔

#### Scenario: Empty result set
- **WHEN** 当前项目在所选筛选条件下没有任何伏笔条目
- **THEN** 面板必须展示明确的空状态提示

### Requirement: Users SHALL be able to manually register a foreshadow item

The system SHALL allow users to manually register a foreshadow item from the panel. 登记表单至少必须支持 `title`、`type`、`note` 三项输入；当当前激活卡片为章节正文时，系统必须默认将该章节绑定为 `chapter_id`，但不得阻止用户创建不绑定章节的项目级伏笔。

#### Scenario: Register from chapter content
- **WHEN** 用户在章节正文卡片下打开伏笔面板并提交合法表单
- **THEN** 系统必须创建一条新的伏笔登记
- **AND** 新条目必须默认关联当前章节卡片 id

#### Scenario: Register from non-chapter card
- **WHEN** 用户在非章节卡片下提交合法表单
- **THEN** 系统必须创建一条新的项目级伏笔登记
- **AND** 该条目可以不包含 `chapter_id`

#### Scenario: Missing required title
- **WHEN** 用户提交缺少标题的登记表单
- **THEN** 系统必须阻止提交并提示标题为必填项

### Requirement: Users SHALL be able to act on existing foreshadow items

The system SHALL support resolving, deleting, and navigating from existing foreshadow items. 若伏笔条目包含 `chapter_id`，系统还必须提供跳转到关联章节的能力。

#### Scenario: Resolve an open foreshadow item
- **WHEN** 用户对一条 `open` 伏笔执行“标记已回收”
- **THEN** 系统必须调用回收接口
- **AND** 成功后该条目状态必须更新为 `resolved`

#### Scenario: Delete a foreshadow item
- **WHEN** 用户确认删除一条伏笔
- **THEN** 系统必须调用删除接口
- **AND** 成功后该条目必须从当前列表中移除

#### Scenario: Jump to linked chapter
- **WHEN** 用户点击一条包含 `chapter_id` 的伏笔的“跳转章节”
- **THEN** 系统必须激活对应章节卡片并切换到编辑器主视图

### Requirement: Chapter content SHALL support candidate foreshadow suggestions before registration

The system SHALL provide candidate foreshadow suggestions when the active card is chapter content with analyzable text. 候选建议必须以“待确认”形式展示，只有在用户显式勾选并提交后，系统才可以将其登记为正式伏笔。

#### Scenario: Request suggestions from chapter content
- **WHEN** 用户在章节正文卡片下点击“生成候选建议”
- **THEN** 系统必须使用当前章节文本请求伏笔候选建议
- **AND** 返回结果必须按可识别类别展示给用户

#### Scenario: Register selected suggestions
- **WHEN** 用户勾选一个或多个候选建议并执行登记
- **THEN** 系统必须仅登记被勾选的候选项
- **AND** 每个登记条目必须默认绑定当前章节卡片 id

#### Scenario: No chapter text available
- **WHEN** 当前章节正文为空或不可分析
- **THEN** 系统不得发起候选建议请求
- **AND** 面板必须提示需要可用正文内容
