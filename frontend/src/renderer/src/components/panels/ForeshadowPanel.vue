<template>
  <div class="foreshadow-panel">
    <div class="panel-header">
      <h3 class="panel-title">伏笔管理</h3>
      <div class="header-actions">
        <el-button size="small" type="primary" @click="openRegisterDialog">手动登记</el-button>
        <el-button v-if="isChapterContent" size="small" @click="openSuggestDialog">生成候选建议</el-button>
      </div>
    </div>

    <div class="filter-tabs">
      <el-radio-group v-model="filterStatus" size="small" @change="handleFilterChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="open">未回收</el-radio-button>
        <el-radio-button label="resolved">已回收</el-radio-button>
      </el-radio-group>
    </div>

    <el-scrollbar class="list-container" v-loading="loading">
      <template v-if="!projectId">
        <div class="empty-state">请先选择项目</div>
      </template>
      <template v-else-if="items.length === 0 && !loading">
        <div class="empty-state">{{ emptyStateText }}</div>
      </template>
      <template v-else>
        <div class="item-card" v-for="item in items" :key="item.id">
          <div class="item-header">
            <span class="item-title">{{ item.title }}</span>
            <el-tag :type="typeTagType(item.type)" size="small">{{ typeLabel(item.type) }}</el-tag>
          </div>
          <div v-if="item.note" class="item-note">{{ item.note }}</div>
          <div class="item-meta">
            <span class="meta-item">{{ formatDate(item.created_at) }}</span>
            <el-tag v-if="item.chapter_id" size="small" type="info" effect="plain">关联章节</el-tag>
            <el-tag :type="item.status === 'open' ? 'warning' : 'success'" size="small" effect="plain">
              {{ item.status === 'open' ? '未回收' : '已回收' }}
            </el-tag>
          </div>
          <div class="item-actions">
            <el-button v-if="item.status === 'open'" size="small" type="success" plain @click="handleResolve(item)">
              标记回收
            </el-button>
            <el-button v-if="item.chapter_id" size="small" plain @click="handleJumpToChapter(item)">
              跳转章节
            </el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(item)">删除</el-button>
          </div>
        </div>
      </template>
    </el-scrollbar>

    <!-- 手动登记对话框 -->
    <el-dialog v-model="registerDialogVisible" title="手动登记伏笔" width="500px">
      <el-form :model="registerForm" label-width="70px">
        <el-form-item label="标题" required>
          <el-input v-model="registerForm.title" placeholder="请输入伏笔标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="registerForm.type" placeholder="选择类型">
            <el-option label="目标" value="goal" />
            <el-option label="道具" value="item" />
            <el-option label="人物" value="person" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="registerForm.note" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item v-if="isChapterContent" label="关联">
          <el-tag size="small" type="info">将自动关联当前章节</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRegister">确认登记</el-button>
      </template>
    </el-dialog>

    <!-- 候选建议对话框 -->
    <el-dialog v-model="suggestDialogVisible" title="候选伏笔建议" width="600px">
      <div v-loading="suggestionsLoading">
        <template v-if="suggestions && !suggestionsLoading">
          <template v-if="hasAnySuggestions">
            <div v-if="suggestions.goals.length > 0" class="suggest-group">
              <div class="suggest-group-title">🎯 目标类</div>
              <el-checkbox-group v-model="selectedSuggestions">
                <el-checkbox v-for="goal in suggestions.goals" :key="goal" :label="goal">
                  {{ goal }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
            <div v-if="suggestions.items.length > 0" class="suggest-group">
              <div class="suggest-group-title">📦 道具类</div>
              <el-checkbox-group v-model="selectedSuggestions">
                <el-checkbox v-for="item in suggestions.items" :key="item" :label="item">
                  {{ item }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
            <div v-if="suggestions.persons.length > 0" class="suggest-group">
              <div class="suggest-group-title">👤 人物类</div>
              <el-checkbox-group v-model="selectedSuggestions">
                <el-checkbox v-for="person in suggestions.persons" :key="person" :label="person">
                  {{ person }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </template>
          <div v-else class="empty-suggestions">
            未识别到候选伏笔,请手动登记
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="suggestDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="selectedSuggestions.length === 0" @click="submitSelectedSuggestions">
          登记选中项 ({{ selectedSuggestions.length }})
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  foreshadowSuggest,
  listForeshadow,
  registerForeshadow,
  resolveForeshadow,
  deleteForeshadow,
  type ForeshadowItem,
  type ForeshadowResponse
} from '@renderer/api/ai'
import type { CardRead } from '@renderer/api/cards'

const props = defineProps<{
  projectId: number | undefined
  activeCard: CardRead | null
  isChapterContent: boolean
}>()

const emit = defineEmits<{
  (e: 'jump-to-card', payload: { projectId: number; cardId: number }): void
}>()

// 列表状态
const items = ref<ForeshadowItem[]>([])
const loading = ref(false)
const filterStatus = ref<'all' | 'open' | 'resolved'>('all')

// 手动登记表单
const registerForm = ref({
  title: '',
  type: 'other' as 'goal' | 'item' | 'person' | 'other',
  note: ''
})
const registerDialogVisible = ref(false)

// 候选建议
const suggestions = ref<ForeshadowResponse | null>(null)
const suggestionsLoading = ref(false)
const selectedSuggestions = ref<string[]>([])
const suggestDialogVisible = ref(false)

// 建立候选项到类型的映射
const suggestionTypeMap = ref<Map<string, 'goal' | 'item' | 'person'>>(new Map())

const emptyStateText = computed(() => {
  switch (filterStatus.value) {
    case 'open': return '暂无未回收伏笔'
    case 'resolved': return '暂无已回收伏笔'
    default: return '暂无伏笔登记'
  }
})

const hasAnySuggestions = computed(() => {
  if (!suggestions.value) return false
  return suggestions.value.goals.length > 0 ||
         suggestions.value.items.length > 0 ||
         suggestions.value.persons.length > 0
})

// 加载伏笔列表
async function loadForeshadowList() {
  if (!props.projectId) return

  loading.value = true
  try {
    const status = filterStatus.value === 'all' ? undefined : filterStatus.value
    const result = await listForeshadow(props.projectId, status)
    items.value = result.items.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } catch (error) {
    ElMessage.error('加载伏笔列表失败')
  } finally {
    loading.value = false
  }
}

// 筛选变化
function handleFilterChange() {
  loadForeshadowList()
}

// 打开手动登记对话框
function openRegisterDialog() {
  registerForm.value = {
    title: '',
    type: 'other',
    note: ''
  }
  registerDialogVisible.value = true
}

// 提交手动登记
async function submitRegister() {
  if (!registerForm.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }

  if (!props.projectId) return

  try {
    const chapterId = props.isChapterContent && props.activeCard ? props.activeCard.id : undefined

    await registerForeshadow(props.projectId, [{
      title: registerForm.value.title.trim(),
      type: registerForm.value.type,
      note: registerForm.value.note.trim() || undefined,
      chapter_id: chapterId
    }])

    ElMessage.success('登记成功')
    registerDialogVisible.value = false
    await loadForeshadowList()
  } catch (error) {
    ElMessage.error('登记失败')
  }
}

// 打开候选建议对话框
async function openSuggestDialog() {
  if (!props.isChapterContent) {
    ElMessage.warning('仅章节正文支持候选建议')
    return
  }

  const chapterText = extractChapterText(props.activeCard)
  if (!chapterText || chapterText.length < 10) {
    ElMessage.warning('章节正文内容不足,无法生成建议')
    return
  }

  suggestDialogVisible.value = true
  suggestionsLoading.value = true
  selectedSuggestions.value = []
  suggestionTypeMap.value.clear()

  try {
    suggestions.value = await foreshadowSuggest(chapterText)

    // 建立映射
    suggestions.value.goals.forEach(g => suggestionTypeMap.value.set(g, 'goal'))
    suggestions.value.items.forEach(i => suggestionTypeMap.value.set(i, 'item'))
    suggestions.value.persons.forEach(p => suggestionTypeMap.value.set(p, 'person'))
  } catch (error) {
    ElMessage.error('生成候选建议失败')
  } finally {
    suggestionsLoading.value = false
  }
}

// 提取章节文本
function extractChapterText(card: CardRead | null): string {
  if (!card) return ''
  return (card.content as any)?.content || ''
}

// 提交选中的候选建议
async function submitSelectedSuggestions() {
  if (selectedSuggestions.value.length === 0) {
    ElMessage.warning('请至少勾选一个候选项')
    return
  }

  if (!props.projectId || !props.activeCard) return

  try {
    const items = selectedSuggestions.value.map(text => ({
      title: text,
      type: suggestionTypeMap.value.get(text) || 'other',
      chapter_id: props.activeCard!.id
    }))

    await registerForeshadow(props.projectId, items)
    ElMessage.success(`已登记 ${items.length} 条伏笔`)
    suggestDialogVisible.value = false
    await loadForeshadowList()
  } catch (error) {
    ElMessage.error('批量登记失败')
  }
}

// 标记回收
async function handleResolve(item: ForeshadowItem) {
  if (item.status === 'resolved' || !props.projectId) return

  try {
    await resolveForeshadow(props.projectId, item.id)
    ElMessage.success('已标记为回收')
    await loadForeshadowList()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 删除
async function handleDelete(item: ForeshadowItem) {
  if (!props.projectId) return

  try {
    await ElMessageBox.confirm('确认删除此伏笔?', '提示', {
      type: 'warning'
    })

    await deleteForeshadow(props.projectId, item.id)
    ElMessage.success('已删除')
    await loadForeshadowList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 跳转到章节
function handleJumpToChapter(item: ForeshadowItem) {
  if (!item.chapter_id || !props.projectId) {
    ElMessage.warning('该伏笔未关联章节')
    return
  }

  emit('jump-to-card', {
    projectId: props.projectId,
    cardId: item.chapter_id
  })
}

// 工具函数
function typeLabel(type: string): string {
  const map: Record<string, string> = {
    goal: '目标',
    item: '道具',
    person: '人物',
    other: '其他'
  }
  return map[type] || '其他'
}

function typeTagType(type: string): 'success' | 'warning' | 'info' | 'danger' | '' {
  const map: Record<string, any> = {
    goal: 'warning',
    item: 'success',
    person: 'info',
    other: ''
  }
  return map[type] || ''
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 监听项目变化
watch(() => props.projectId, () => {
  filterStatus.value = 'all'
  loadForeshadowList()
})

onMounted(() => {
  if (props.projectId) {
    loadForeshadowList()
  }
})
</script>

<style scoped>
.foreshadow-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-tabs {
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.list-container {
  flex: 1;
  padding: 12px 16px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.item-card {
  margin-bottom: 12px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  border: 1px solid var(--el-border-color-lighter);
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.item-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
  flex: 1;
  margin-right: 8px;
}

.item-note {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-item {
  color: var(--el-text-color-secondary);
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.suggest-group {
  margin-bottom: 20px;
}

.suggest-group:last-child {
  margin-bottom: 0;
}

.suggest-group-title {
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.suggest-group :deep(.el-checkbox-group) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-suggestions {
  text-align: center;
  padding: 40px 20px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
