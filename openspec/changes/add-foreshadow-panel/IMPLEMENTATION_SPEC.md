# Foreshadow Panel Implementation OpenSpec

## Context & Goal

为编辑器右侧侧栏添加"伏笔"面板,复用现有后端 API,支持项目级伏笔查看、筛选、登记、回收、删除和章节跳转。

## Interface Definitions

### 1. ForeshadowPanel.vue Component Props

```typescript
interface ForeshadowPanelProps {
  projectId: number | undefined          // 当前项目 ID
  activeCard: CardRead | null            // 当前激活卡片
  isChapterContent: boolean              // 是否为章节正文卡片
}

interface ForeshadowPanelEmits {
  (e: 'jump-to-card', payload: { projectId: number; cardId: number }): void
}
```

### 2. Editor.vue Integration Points

**Modified Computed:**
```typescript
const rightSidebarTabNames = computed(() => {
  if (!showRightSidebarTabs.value) return []
  if (isChapterContent.value) {
    return ['assistant', 'context', 'extract', 'outline', 'foreshadow', 'review-history']
  }
  return ['assistant', 'foreshadow', 'review-history']
})
```

**New Tab Pane:**
```vue
<el-tab-pane label="伏笔" name="foreshadow">
  <ForeshadowPanel
    :project-id="projectStore.currentProject?.id"
    :active-card="activeCard"
    :is-chapter-content="isChapterContent"
    @jump-to-card="handleJumpToCard"
  />
</el-tab-pane>
```

### 3. API Functions (Already Exist in ai.ts)

```typescript
// 候选建议
foreshadowSuggest(text: string): Promise<ForeshadowResponse>

// 列表查询
listForeshadow(projectId: number, status?: 'open' | 'resolved'): Promise<ForeshadowListResponse>

// 登记
registerForeshadow(
  projectId: number,
  items: Array<{ title: string; type?: string; note?: string; chapter_id?: number }>
): Promise<ForeshadowListResponse>

// 标记回收
resolveForeshadow(projectId: number, itemId: number): Promise<ForeshadowItem>

// 删除
deleteForeshadow(projectId: number, itemId: number): Promise<{ success: boolean }>
```

## Data Structures

### ForeshadowItem (from ai.ts)

```typescript
interface ForeshadowItem {
  id: number
  project_id: number
  chapter_id?: number | null
  title: string
  type: 'goal' | 'item' | 'person' | 'other'
  note?: string | null
  status: 'open' | 'resolved'
  created_at: string
  resolved_at?: string | null
}
```

### ForeshadowResponse (Suggest API)

```typescript
interface ForeshadowResponse {
  goals: string[]      // 目标类候选
  items: string[]      // 道具类候选
  persons: string[]    // 人物类候选
}
```

### Component Local State

```typescript
interface ForeshadowPanelState {
  // 列表数据
  items: ForeshadowItem[]
  loading: boolean

  // 筛选状态
  filterStatus: 'all' | 'open' | 'resolved'

  // 手动登记表单
  registerForm: {
    title: string
    type: 'goal' | 'item' | 'person' | 'other'
    note: string
  }
  registerDialogVisible: boolean

  // 候选建议
  suggestions: ForeshadowResponse | null
  suggestionsLoading: boolean
  selectedSuggestions: Set<string>  // 勾选的候选项
  suggestDialogVisible: boolean
}
```

## Logic Flow

### 1. Component Initialization

```
onMounted:
  IF projectId exists:
    CALL loadForeshadowList('all')
  ELSE:
    SHOW empty state "请先选择项目"

watch(projectId):
  IF projectId changes:
    RESET filterStatus to 'all'
    CALL loadForeshadowList('all')
```

### 2. Load Foreshadow List

```
FUNCTION loadForeshadowList(status: 'all' | 'open' | 'resolved'):
  IF NOT projectId:
    RETURN

  SET loading = true
  TRY:
    IF status === 'all':
      result = await listForeshadow(projectId)
    ELSE:
      result = await listForeshadow(projectId, status)

    SET items = result.items
    SORT items by created_at DESC
  CATCH error:
    ElMessage.error('加载伏笔列表失败')
  FINALLY:
    SET loading = false
```

### 3. Manual Registration

```
FUNCTION openRegisterDialog():
  RESET registerForm
  IF isChapterContent AND activeCard:
    // 预填充章节信息(仅用于提示,实际提交时再获取)
  SET registerDialogVisible = true

FUNCTION submitRegister():
  IF NOT registerForm.title.trim():
    ElMessage.warning('标题不能为空')
    RETURN

  TRY:
    chapterId = isChapterContent ? activeCard.id : undefined

    await registerForeshadow(projectId, [{
      title: registerForm.title.trim(),
      type: registerForm.type,
      note: registerForm.note.trim() || undefined,
      chapter_id: chapterId
    }])

    ElMessage.success('登记成功')
    SET registerDialogVisible = false
    CALL loadForeshadowList(filterStatus)
  CATCH error:
    ElMessage.error('登记失败')
```

### 4. Candidate Suggestions (Chapter Context Only)

```
FUNCTION openSuggestDialog():
  IF NOT isChapterContent:
    ElMessage.warning('仅章节正文支持候选建议')
    RETURN

  chapterText = extractChapterText(activeCard)
  IF NOT chapterText OR chapterText.length < 10:
    ElMessage.warning('章节正文内容不足,无法生成建议')
    RETURN

  SET suggestDialogVisible = true
  SET suggestionsLoading = true

  TRY:
    suggestions = await foreshadowSuggest(chapterText)
    SET suggestions = suggestions
    SET selectedSuggestions = new Set()
  CATCH error:
    ElMessage.error('生成候选建议失败')
  FINALLY:
    SET suggestionsLoading = false

FUNCTION extractChapterText(card: CardRead): string:
  RETURN card.content?.content || ''

FUNCTION toggleSuggestion(text: string, category: 'goal' | 'item' | 'person'):
  IF selectedSuggestions.has(text):
    selectedSuggestions.delete(text)
  ELSE:
    selectedSuggestions.add(text)
    // 记录类别映射用于提交
    suggestionTypeMap.set(text, category)

FUNCTION submitSelectedSuggestions():
  IF selectedSuggestions.size === 0:
    ElMessage.warning('请至少勾选一个候选项')
    RETURN

  items = Array.from(selectedSuggestions).map(text => ({
    title: text,
    type: suggestionTypeMap.get(text) || 'other',
    chapter_id: activeCard.id
  }))

  TRY:
    await registerForeshadow(projectId, items)
    ElMessage.success(`已登记 ${items.length} 条伏笔`)
    SET suggestDialogVisible = false
    CALL loadForeshadowList(filterStatus)
  CATCH error:
    ElMessage.error('批量登记失败')
```

### 5. Item Actions

```
FUNCTION handleResolve(item: ForeshadowItem):
  IF item.status === 'resolved':
    RETURN

  TRY:
    await resolveForeshadow(projectId, item.id)
    ElMessage.success('已标记为回收')
    CALL loadForeshadowList(filterStatus)
  CATCH error:
    ElMessage.error('操作失败')

FUNCTION handleDelete(item: ForeshadowItem):
  ElMessageBox.confirm('确认删除此伏笔?', '提示', {
    type: 'warning'
  }).then(async () => {
    TRY:
      await deleteForeshadow(projectId, item.id)
      ElMessage.success('已删除')
      CALL loadForeshadowList(filterStatus)
    CATCH error:
      ElMessage.error('删除失败')
  }).catch(() => {})

FUNCTION handleJumpToChapter(item: ForeshadowItem):
  IF NOT item.chapter_id:
    ElMessage.warning('该伏笔未关联章节')
    RETURN

  emit('jump-to-card', {
    projectId: projectId,
    cardId: item.chapter_id
  })
```

## Edge Cases

### 1. No Project Selected
**Condition:** `projectId` is undefined
**Handling:** Display placeholder "请先选择项目"，禁用所有操作按钮

### 2. Empty List
**Condition:** `items.length === 0` after successful load
**Handling:** Display empty state based on filter:
- `all`: "暂无伏笔登记"
- `open`: "暂无未回收伏笔"
- `resolved`: "暂无已回收伏笔"

### 3. Non-Chapter Context Suggestions
**Condition:** User clicks "生成候选建议" when `isChapterContent === false`
**Handling:** Show warning "仅章节正文支持候选建议"

### 4. Empty Chapter Text
**Condition:** Chapter content is empty or too short (< 10 chars)
**Handling:** Show warning "章节正文内容不足,无法生成建议"

### 5. No Suggestions Returned
**Condition:** API returns empty arrays for all categories
**Handling:** Display "未识别到候选伏笔,请手动登记"

### 6. Jump to Deleted Chapter
**Condition:** `chapter_id` exists but card was deleted
**Handling:** `handleJumpToCard` in Editor.vue will handle gracefully (existing logic)

### 7. Concurrent Operations
**Condition:** User triggers multiple actions rapidly
**Handling:** Use `loading` state to disable buttons during API calls

### 8. Filter State Persistence
**Condition:** User switches between tabs
**Handling:** Filter state is component-local, resets to 'all' on remount (acceptable for MVP)

## UI Layout Structure

```
ForeshadowPanel
├── Header
│   ├── Title: "伏笔管理"
│   ├── Filter Tabs: [全部 | 未回收 | 已回收]
│   └── Actions
│       ├── Button: "手动登记"
│       └── Button: "生成候选建议" (仅章节正文可见)
├── List (el-scrollbar)
│   └── Item Card (v-for)
│       ├── Title + Type Badge
│       ├── Note (if exists)
│       ├── Meta: created_at, chapter_id (if exists)
│       └── Actions
│           ├── Button: "标记回收" (仅 open 状态)
│           ├── Button: "跳转章节" (仅有 chapter_id)
│           └── Button: "删除"
└── Empty State (v-if items.length === 0)

Dialogs:
├── Register Dialog
│   ├── Input: title (required)
│   ├── Select: type [目标 | 道具 | 人物 | 其他]
│   └── Textarea: note (optional)
└── Suggest Dialog
    ├── Loading State
    └── Suggestion Groups
        ├── Goals (checkbox list)
        ├── Items (checkbox list)
        └── Persons (checkbox list)
```

## Implementation Constraints

1. **Minimal Change Principle:** 不修改现有 API 封装,不新增后端端点
2. **Reuse Existing Patterns:** 参考 ContextPanel.vue 的结构和样式
3. **No Global State:** 使用组件局部状态,不引入新的 Pinia store
4. **Type Safety:** 复用 `ai.ts` 中已定义的类型
5. **Accessibility:** 使用 Element Plus 组件确保基础可访问性

## File Changes Summary

**New Files:**
- `frontend/src/renderer/src/components/panels/ForeshadowPanel.vue`

**Modified Files:**
- `frontend/src/renderer/src/views/Editor.vue`
  - Import ForeshadowPanel
  - Add 'foreshadow' to rightSidebarTabNames
  - Add el-tab-pane for foreshadow

**No Changes:**
- `frontend/src/renderer/src/api/ai.ts` (API already exists)
- Backend files (no new endpoints needed)
