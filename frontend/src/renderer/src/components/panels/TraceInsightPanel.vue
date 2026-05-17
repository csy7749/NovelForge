<template>
  <div class="trace-insight-panel">
    <div class="panel-toolbar">
      <div class="title-block">
        <span class="panel-title">上下文洞察</span>
        <span class="panel-subtitle">{{ scopeLabel }}</span>
      </div>
      <el-tooltip content="刷新执行痕迹" placement="bottom">
        <el-button :icon="Refresh" circle size="small" :loading="loading" @click="loadRuns" />
      </el-tooltip>
    </div>

    <el-alert
      v-if="errorMessage"
      class="state-alert"
      type="error"
      :closable="false"
      :title="errorMessage"
      show-icon
    />

    <el-empty
      v-if="!loading && !runs.length && !errorMessage"
      description="暂无执行痕迹"
      :image-size="72"
    />

    <div v-else class="run-list">
      <section v-for="run in runs" :key="run.id" class="run-section">
        <div class="run-header">
          <div class="run-title">{{ run.title }}</div>
          <el-tag size="small" :type="statusTagType(run.status)" effect="plain">
            {{ run.statusLabel }}
          </el-tag>
        </div>

        <div class="step-list">
          <article v-for="step in run.steps" :key="step.id" class="step-card">
            <div class="step-line">
              <div class="step-icon" :class="`kind-${step.status}`">
                <el-icon><component :is="iconForStep(step.kindLabel)" /></el-icon>
              </div>
              <div class="step-main">
                <div class="step-meta">
                  <span class="step-time">{{ step.timeLabel }}</span>
                  <el-tag size="small" :type="statusTagType(step.status)" effect="plain">
                    {{ step.statusLabel }}
                  </el-tag>
                  <el-tag size="small" effect="plain">{{ step.kindLabel }}</el-tag>
                </div>
                <div class="step-title">{{ step.description }}</div>
                <div v-if="step.inputPreview" class="summary-line">
                  输入：{{ step.inputPreview }}
                </div>
                <div v-if="step.outputPreview" class="summary-line">
                  输出：{{ step.outputPreview }}
                </div>
                <div v-if="step.error" class="error-line">错误：{{ step.error }}</div>

                <div v-if="step.sources.length" class="source-list">
                  <button
                    v-for="source in step.sources"
                    :key="source.id"
                    type="button"
                    class="source-chip"
                    :class="{ clickable: source.clickable }"
                    @click="handleSourceClick(source)"
                  >
                    <span class="source-label">{{ source.label }}</span>
                    <span class="source-preview">{{ source.preview }}</span>
                  </button>
                </div>

                <div v-if="step.spanSnippets.length" class="span-list">
                  <el-tooltip
                    v-for="span in step.spanSnippets"
                    :key="span.id"
                    :content="span.sourceLabel"
                    placement="top"
                  >
                    <mark class="span-highlight">{{ span.text }}</mark>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue'
import { Document, Refresh, Search, Tools, WarningFilled } from '@element-plus/icons-vue'

import { listTraceRuns } from '@renderer/api/aiTraces'
import type { TraceSourceView, TraceRunView } from '@renderer/services/traceInsightView'
import { toTraceRunView } from '@renderer/services/traceInsightView'

const POLL_INTERVAL_MS = 3000

const props = defineProps<{
  projectId?: number | null
  cardId?: number | null
}>()

const emit = defineEmits<{
  'jump-to-card': [{ projectId: number; cardId: number }]
}>()

const loading = ref(false)
const errorMessage = ref('')
const runs = ref<TraceRunView[]>([])
let pollTimer: number | null = null

const scopeLabel = computed(() => {
  if (props.cardId) return `当前卡片 #${props.cardId}`
  if (props.projectId) return `当前项目 #${props.projectId}`
  return '未选择项目'
})

const hasRunningRun = computed(() => runs.value.some((run) => run.status === 'running'))

async function loadRuns(): Promise<void> {
  if (!props.projectId) {
    runs.value = []
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const data = await listTraceRuns({
      projectId: props.projectId,
      cardId: props.cardId,
      limit: 10
    })
    runs.value = data.map(toTraceRunView)
  } catch (error: unknown) {
    errorMessage.value = error instanceof Error ? error.message : '执行痕迹加载失败'
  } finally {
    loading.value = false
  }
}

function handleSourceClick(source: TraceSourceView): void {
  if (!source.clickable || !source.jumpTarget) return
  const projectId = Number(source.jumpTarget.project_id || props.projectId || 0)
  const cardId = Number(source.jumpTarget.card_id || 0)
  if (!projectId || !cardId) return
  emit('jump-to-card', { projectId, cardId })
}

function statusTagType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'cancelled') return 'warning'
  return 'info'
}

function iconForStep(kindLabel: string): Component {
  if (kindLabel === '工具') return Tools
  if (kindLabel === '上下文') return Search
  if (kindLabel === '错误') return WarningFilled
  return Document
}

function startPolling(): void {
  stopPolling()
  pollTimer = window.setInterval(() => {
    if (props.projectId && (hasRunningRun.value || document.visibilityState === 'visible')) {
      void loadRuns()
    }
  }, POLL_INTERVAL_MS)
}

function stopPolling(): void {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => [props.projectId, props.cardId],
  () => {
    void loadRuns()
  },
  { immediate: true }
)

onMounted(startPolling)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.trace-insight-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--el-bg-color);
}

.panel-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.title-block {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.panel-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.panel-subtitle {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-alert {
  margin: 10px 12px 0;
}

.run-list {
  flex: 1;
  overflow: auto;
  padding: 10px 12px 16px;
}

.run-section + .run-section {
  margin-top: 16px;
}

.run-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.run-title {
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.step-line {
  display: flex;
  gap: 10px;
  padding: 10px;
}

.step-icon {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border-radius: 50%;
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.kind-failed {
  color: var(--el-color-danger);
}

.kind-running {
  color: var(--el-color-warning);
}

.step-main {
  min-width: 0;
  flex: 1;
}

.step-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.step-time {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.step-title {
  color: var(--el-text-color-primary);
  font-size: 13px;
  line-height: 1.45;
}

.summary-line,
.error-line {
  margin-top: 6px;
  overflow-wrap: anywhere;
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.45;
}

.error-line {
  color: var(--el-color-danger);
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.source-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding: 7px 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-fill-color-extra-light);
  color: inherit;
  text-align: left;
}

.source-chip.clickable {
  cursor: pointer;
}

.source-chip.clickable:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.source-label {
  color: var(--el-text-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.source-preview {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.span-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.span-highlight {
  padding: 1px 4px;
  border-radius: 4px;
  background: var(--el-color-warning-light-8);
  color: var(--el-text-color-primary);
  font-size: 12px;
}
</style>
