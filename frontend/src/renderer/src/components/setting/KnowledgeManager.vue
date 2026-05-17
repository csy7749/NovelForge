<template>
  <div class="knowledge-manager">
    <div class="toolbar">
      <el-input
        v-model="filters.query"
        clearable
        placeholder="搜索名称、摘要或内容"
        style="width: 220px"
        @keyup.enter="fetchList"
      />
      <el-select v-model="filters.knowledge_type" clearable placeholder="类型" style="width: 140px">
        <el-option
          v-for="type in metadata.knowledge_types"
          :key="type"
          :label="typeLabels[type]"
          :value="type"
        />
      </el-select>
      <el-checkbox v-model="filters.is_injectable" :true-value="true" :false-value="undefined">
        仅可注入
      </el-checkbox>
      <el-button size="small" @click="fetchList">检索</el-button>
      <el-button type="primary" size="small" @click="openEditor()">新建知识</el-button>
    </div>

    <el-table :data="items" height="60vh" size="small" v-loading="loading">
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small">{{ typeLabels[row.knowledge_type] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="注入" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_injectable ? 'success' : 'info'">
            {{ row.is_injectable ? modeLabels[row.injection_mode] : '不注入' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="150" />
      <el-table-column label="摘要" min-width="180">
        <template #default="{ row }">{{ row.summary || '-' }}</template>
      </el-table-column>
      <el-table-column label="内置" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.built_in ? 'info' : 'success'">
            {{ row.built_in ? '内置' : '自定义' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditor(row)">编辑</el-button>
          <el-popconfirm title="删除该知识？" @confirm="remove(row)">
            <template #reference>
              <el-button size="small" type="danger" plain :disabled="row.built_in">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="editor.visible"
      :title="editor.editing ? '编辑知识' : '新建知识'"
      width="58%"
      append-to-body
    >
      <el-form label-position="top" :model="editor.form">
        <div class="form-grid">
          <el-form-item label="名称">
            <el-input v-model="editor.form.name" :disabled="editor.editing && editor.form.built_in" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="editor.form.knowledge_type" style="width: 100%">
              <el-option
                v-for="type in metadata.knowledge_types"
                :key="type"
                :label="typeLabels[type]"
                :value="type"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="editor.form.description" type="textarea" :rows="2" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="启用上下文注入">
            <el-switch v-model="editor.form.is_injectable" @change="onInjectionToggle" />
          </el-form-item>
          <el-form-item label="注入模式">
            <el-select
              v-model="editor.form.injection_mode"
              :disabled="!editor.form.is_injectable"
              style="width: 100%"
            >
              <el-option label="全文" value="full" />
              <el-option label="摘要" value="summary" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="摘要">
          <el-input v-model="editor.form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editor.form.content" type="textarea" :rows="12" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="来源">
            <el-input v-model="editor.form.source" />
          </el-form-item>
          <el-form-item label="维护说明">
            <el-input v-model="editor.form.maintenance_notes" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editor.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createKnowledge,
  deleteKnowledge,
  getKnowledgeMetadata,
  listKnowledge,
  updateKnowledge,
  type InjectionMode,
  type Knowledge,
  type KnowledgeMetadata,
  type KnowledgeType
} from '@renderer/api/setting'
import { resetKnowledgeOptionCache } from '@renderer/services/knowledgeOptionResolver'

const typeLabels: Record<KnowledgeType, string> = {
  design: '设计',
  memory: '记忆',
  skill: '技能',
  reference: '参考'
}

const modeLabels: Record<InjectionMode, string> = {
  none: '不注入',
  full: '全文',
  summary: '摘要'
}

const defaultMetadata: KnowledgeMetadata = {
  knowledge_types: ['design', 'memory', 'skill', 'reference'],
  injection_modes: ['none', 'full', 'summary'],
  retrieval_backends: ['keyword', 'semantic']
}

const loading = ref(false)
const items = ref<Knowledge[]>([])
const metadata = ref<KnowledgeMetadata>(defaultMetadata)
const filters = ref<{ query?: string; knowledge_type?: KnowledgeType; is_injectable?: boolean }>({})
const editor = ref<{ visible: boolean; editing: boolean; form: Partial<Knowledge> }>({
  visible: false,
  editing: false,
  form: {}
})

async function fetchMetadata() {
  metadata.value = await getKnowledgeMetadata()
}

async function fetchList() {
  loading.value = true
  try {
    items.value = await listKnowledge(filters.value)
  } catch {
    ElMessage.error('加载知识库失败')
  } finally {
    loading.value = false
  }
}

function emptyForm(): Partial<Knowledge> {
  return {
    name: '',
    description: '',
    content: '',
    knowledge_type: 'reference',
    summary: '',
    summary_enabled: false,
    is_injectable: false,
    injection_mode: 'none',
    source: '',
    maintenance_notes: ''
  }
}

function openEditor(row?: Knowledge) {
  editor.value.visible = true
  editor.value.editing = !!row
  editor.value.form = row ? { ...row } : emptyForm()
}

function onInjectionToggle(value: boolean | string | number) {
  const form = editor.value.form
  form.injection_mode = value ? 'full' : 'none'
}

function buildPayload(form: Partial<Knowledge>) {
  const isInjectable = !!form.is_injectable
  return {
    name: form.name || '',
    description: form.description || '',
    content: form.content || '',
    knowledge_type: form.knowledge_type || 'reference',
    summary: form.summary || '',
    summary_enabled: !!form.summary,
    is_injectable: isInjectable,
    injection_mode: isInjectable ? form.injection_mode || 'full' : 'none',
    injection_config: form.injection_config || null,
    source: form.source || '',
    maintenance_notes: form.maintenance_notes || ''
  }
}

function validatePayload(payload: ReturnType<typeof buildPayload>): boolean {
  if (!payload.name || !payload.content) {
    ElMessage.warning('请填写名称与内容')
    return false
  }
  if (payload.injection_mode === 'summary' && !payload.summary) {
    ElMessage.warning('摘要注入模式必须填写摘要')
    return false
  }
  return true
}

async function save() {
  try {
    const payload = buildPayload(editor.value.form)
    if (!validatePayload(payload)) return
    const saved = await persistKnowledge(payload)
    resetKnowledgeOptionCache()
    upsertItem(saved)
    ElMessage.success(editor.value.editing ? '已更新' : '已创建')
    editor.value.visible = false
  } catch (error: any) {
    ElMessage.error(error?.message || '保存失败')
  }
}

async function persistKnowledge(payload: ReturnType<typeof buildPayload>) {
  const id = editor.value.form.id
  if (editor.value.editing && id) {
    return await updateKnowledge(id, payload)
  }
  return await createKnowledge(payload)
}

function upsertItem(saved: Knowledge) {
  const index = items.value.findIndex((item) => item.id === saved.id)
  if (index >= 0) {
    items.value[index] = saved
    return
  }
  items.value.unshift(saved)
}

async function remove(row: Knowledge) {
  try {
    await deleteKnowledge(row.id)
    resetKnowledgeOptionCache()
    ElMessage.success('已删除')
    items.value = items.value.filter((item) => item.id !== row.id)
  } catch (error: any) {
    ElMessage.error(error?.message || '删除失败')
  }
}

async function init() {
  await fetchMetadata()
  await fetchList()
}

init()
</script>

<style scoped>
.knowledge-manager {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
