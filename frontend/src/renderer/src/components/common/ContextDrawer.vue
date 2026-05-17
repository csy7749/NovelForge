<template>
  <el-drawer v-model="visible" :with-header="false" size="42%" append-to-body>
    <div class="drawer-wrapper">
      <div class="drawer-header">
        <h3>上下文注入</h3>
        <el-button text @click="visible = false">关闭</el-button>
      </div>

      <div class="section">
        <div class="slot-toolbar">
          <h4>上下文模板</h4>
          <div class="slot-buttons">
            <el-button
              v-for="kind in contextTemplateKinds"
              :key="kind"
              size="small"
              :type="activeContextTemplateKind === kind ? 'primary' : 'default'"
              plain
              @click="activeContextTemplateKind = kind"
            >
              {{ contextTemplateLabels[kind] }}
            </el-button>
          </div>
        </div>
        <el-input
          v-model="aiContext"
          type="textarea"
          :rows="7"
          placeholder="在此编辑上下文模板，支持 @ 引用"
          class="context-area"
          :spellcheck="false"
        />
        <div class="chips">
          <el-tag v-for="(t, i) in tokens" :key="i" closable @close="removeToken(t)">@{{ t }}</el-tag>
        </div>
        <div class="actions">
          <el-button size="small" @click="$emit('open-selector', { kind: activeContextTemplateKind, text: aiContext })">
            插入引用 @
          </el-button>
          <el-button size="small" type="primary" @click="apply">应用到卡片</el-button>
        </div>
      </div>

      <div class="visualization">
        <div class="visualization-head">
          <h4>上下文可视化</h4>
          <el-tag size="small" :type="statusTagType">{{ statusLabel }}</el-tag>
        </div>

        <el-alert
          v-if="!aiContext.trim()"
          type="info"
          :closable="false"
          show-icon
          title="当前卡片没有可用的上下文模板"
        />

        <el-alert
          v-for="(error, index) in visualization.errors"
          :key="`error-${index}`"
          type="error"
          :closable="false"
          show-icon
          :title="error"
        />

        <el-tabs v-model="activeView" class="context-tabs">
          <el-tab-pane label="模板视图" name="template">
            <div class="template-view">
              <div v-if="templateSegments.length" class="template-highlight">
                <template v-for="segment in templateSegments" :key="segment.id">
                  <span v-if="segment.kind === 'text'">{{ segment.text }}</span>
                  <el-tag v-else size="small" :type="segment.resolved ? 'success' : 'danger'" effect="plain">
                    {{ segment.text }}
                  </el-tag>
                </template>
              </div>
              <el-empty v-else description="空模板" :image-size="72" />
              <div v-if="visualization.tokens.length" class="token-list">
                <div v-for="token in visualization.tokens" :key="`${token.start}-${token.raw}`" class="token-item">
                  <div class="token-main">
                    <span class="token-name">@{{ token.token }}</span>
                    <el-tag size="small" effect="plain">{{ token.label }}</el-tag>
                    <el-tag v-if="!token.resolved" size="small" type="danger" effect="plain">未解析</el-tag>
                  </div>
                  <div class="token-preview">{{ token.preview || '无内容' }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="解析视图" name="resolution">
            <div v-if="visualization.sources.length" class="source-list">
              <div v-for="source in visualization.sources" :key="source.id" class="source-item">
                <div class="source-head">
                  <div class="source-title">
                    <el-tag size="small" effect="plain">{{ sourceKindLabel(source.kind) }}</el-tag>
                    <span>{{ source.label }}</span>
                  </div>
                  <div class="source-meta">
                    <el-tag v-if="source.sourceRef" size="small" type="info" effect="plain">{{ source.sourceRef }}</el-tag>
                    <el-tag size="small" :type="source.state === 'resolved' ? 'success' : 'danger'" effect="plain">
                      {{ source.state === 'resolved' ? `命中 ${source.count}` : '未命中' }}
                    </el-tag>
                    <el-tag v-if="source.truncated" size="small" type="warning" effect="plain">已截断</el-tag>
                  </div>
                </div>
                <pre class="source-preview">{{ source.preview || '无预览内容' }}</pre>
              </div>
            </div>
            <el-empty v-else description="没有解析来源" :image-size="72" />
            <div v-if="visualization.emptySources.length" class="empty-sources">
              <el-tag v-for="item in visualization.emptySources" :key="item" size="small" type="warning" effect="plain">
                {{ emptySourceLabel(item) }}
              </el-tag>
            </div>
          </el-tab-pane>

          <el-tab-pane label="最终注入视图" name="injection">
            <pre v-if="visualization.finalText.trim()" class="final-text">{{ visualization.finalText }}</pre>
            <el-empty v-else description="最终注入内容为空" :image-size="72" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AssembleContextResponse } from '@renderer/api/ai'
import type { CardRead } from '@renderer/api/cards'
import {
  CONTEXT_TEMPLATE_LABELS,
  type ContextTemplateKind,
  type ContextTemplates,
} from '@renderer/services/contextSlots'
import { buildContextVisualizationModel } from '@renderer/services/contextVisualization'

const props = defineProps<{
  modelValue: boolean
  contextTemplates: ContextTemplates
  activeContextTemplateKind: ContextTemplateKind
  cards: CardRead[]
  currentCard?: CardRead
  assembledContext?: AssembleContextResponse | null
  previewText?: string
}>()
const emit = defineEmits(['update:modelValue', 'update:activeContextTemplateKind', 'apply-context', 'open-selector'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, v => visible.value = v)
watch(visible, v => emit('update:modelValue', v))

const contextTemplateKinds: ContextTemplateKind[] = ['generation', 'review']
const contextTemplateLabels = CONTEXT_TEMPLATE_LABELS
const activeContextTemplateKind = ref<ContextTemplateKind>(props.activeContextTemplateKind)
const activeView = ref<'template' | 'resolution' | 'injection'>('template')

watch(() => props.activeContextTemplateKind, v => activeContextTemplateKind.value = v)
watch(activeContextTemplateKind, v => emit('update:activeContextTemplateKind', v))

const localTemplates = ref<ContextTemplates>({ ...props.contextTemplates })
watch(
  () => props.contextTemplates,
  v => {
    localTemplates.value = { ...v }
  },
  { deep: true }
)

const aiContext = computed({
  get: () => localTemplates.value[activeContextTemplateKind.value] || '',
  set: (value: string) => {
    localTemplates.value = {
      ...localTemplates.value,
      [activeContextTemplateKind.value]: value,
    }
  },
})

const visualization = computed(() => buildContextVisualizationModel({
  template: aiContext.value,
  cards: props.cards,
  currentCard: props.currentCard,
  assembledContext: props.assembledContext,
}))

const statusLabel = computed(() => {
  if (!aiContext.value.trim()) return '空模板'
  if (visualization.value.status === 'error') return '装配失败'
  if (visualization.value.status === 'partial') return '部分命中'
  if (visualization.value.status === 'empty') return '无来源'
  return '可用'
})

const statusTagType = computed(() => {
  if (!aiContext.value.trim() || visualization.value.status === 'empty') return 'info'
  if (visualization.value.status === 'error') return 'danger'
  if (visualization.value.status === 'partial') return 'warning'
  return 'success'
})

const tokens = computed(() => visualization.value.tokens.map(token => token.token))

const templateSegments = computed(() => {
  const template = visualization.value.template
  const segments: Array<{ id: string; kind: 'text' | 'token'; text: string; resolved?: boolean }> = []
  let cursor = 0
  visualization.value.tokens.forEach((token, index) => {
    if (token.start > cursor) {
      segments.push({ id: `text-${index}`, kind: 'text', text: template.slice(cursor, token.start) })
    }
    segments.push({ id: `token-${index}`, kind: 'token', text: token.raw, resolved: token.resolved })
    cursor = token.end
  })
  if (cursor < template.length) segments.push({ id: 'text-tail', kind: 'text', text: template.slice(cursor) })
  return segments
})

function removeToken(token: string): void {
  const full = `@${token}`
  aiContext.value = (aiContext.value || '').split(full).join('')
}

function apply(): void {
  emit('apply-context', { kind: activeContextTemplateKind.value, text: aiContext.value })
}

function sourceKindLabel(kind: string): string {
  const labels: Record<string, string> = {
    facts: '事实 token',
    kg: '图谱 token',
    card_reference: '卡片引用',
    facts_subgraph: '事实子图',
    fact_summary: '关键事实',
    facts_relation: '关系摘要',
    item_summary: '物品摘要',
    concept_summary: '概念摘要',
  }
  return labels[kind] || kind
}

function emptySourceLabel(kind: string): string {
  const labels: Record<string, string> = {
    participants: '未提供参与实体',
    facts_structured: '无结构化事实',
    fact_summaries: '无关键事实',
    relation_summaries: '无关系摘要',
    item_summaries: '无物品摘要',
    concept_summaries: '无概念摘要',
  }
  return labels[kind] || kind
}

let drawerTextarea: HTMLTextAreaElement | null = null
watch(() => visible.value, (v) => {
  if (v) {
    setTimeout(() => {
      drawerTextarea = document.querySelector('.context-area textarea') as HTMLTextAreaElement | null
      drawerTextarea?.addEventListener('input', handleDrawerInput)
    }, 0)
  } else {
    drawerTextarea?.removeEventListener('input', handleDrawerInput)
    drawerTextarea = null
  }
})

function handleDrawerInput(ev: Event): void {
  const textarea = ev.target as HTMLTextAreaElement
  const cursorPos = textarea.selectionStart
  const lastChar = textarea.value.substring(cursorPos - 1, cursorPos)
  if (lastChar === '@') {
    emit('open-selector', { kind: activeContextTemplateKind.value, text: textarea.value })
  }
}
</script>

<style scoped>
.drawer-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.drawer-header,
.slot-toolbar,
.visualization-head,
.source-head,
.token-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.drawer-header h3,
.slot-toolbar h4,
.visualization-head h4 {
  margin: 0;
}

.section,
.visualization,
.template-view,
.token-list,
.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slot-buttons,
.actions,
.chips,
.source-meta,
.empty-sources {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.context-area {
  width: 100%;
}

.visualization {
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.context-tabs {
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.context-tabs :deep(.el-tabs__content) {
  height: calc(100% - 48px);
  overflow: auto;
}

.template-highlight {
  white-space: pre-wrap;
  line-height: 1.8;
  padding: 10px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}

.token-item,
.source-item {
  padding: 10px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.token-name,
.source-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.token-preview,
.source-preview,
.final-text {
  margin: 6px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.final-text {
  margin: 0;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
}
</style>
