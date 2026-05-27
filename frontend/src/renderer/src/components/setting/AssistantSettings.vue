<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import { useAssistantPreferences } from '@renderer/composables/useAssistantPreferences'
import {
  listAssistantTools,
  type AssistantToolMetadata
} from '@renderer/api/setting'

// 通过组合式统一管理灵感助手偏好，方便在设置页与助手面板之间复用
const prefs = useAssistantPreferences()
const agentTools = ref<AssistantToolMetadata[]>([])
const toolsLoading = ref(false)
const toolsError = ref('')

const reactModeEnabled = computed({
  get: () => prefs.reactModeEnabled.value,
  set: (val: boolean) => prefs.setReactModeEnabled(val)
})

const assistantTemperature = computed({
  get: () => prefs.assistantTemperature.value,
  set: (val: number | null) => prefs.setAssistantTemperature(val)
})

const assistantMaxTokens = computed({
  get: () => prefs.assistantMaxTokens.value,
  set: (val: number | null) => prefs.setAssistantMaxTokens(val)
})

const assistantTimeout = computed({
  get: () => prefs.assistantTimeout.value,
  set: (val: number | null) => prefs.setAssistantTimeout(val)
})

const toolCountText = computed(() => `${agentTools.value.length} 个工具`)

function formatRiskLevel(riskLevel: string): string {
  const riskLabels: Record<string, string> = {
    low: '低风险',
    medium: '会写入',
    high: '需谨慎'
  }
  return riskLabels[riskLevel] || riskLevel
}

function riskTagType(riskLevel: string): 'info' | 'warning' | 'danger' {
  if (riskLevel === 'high') return 'danger'
  if (riskLevel === 'medium') return 'warning'
  return 'info'
}

function getToolParameterNames(tool: AssistantToolMetadata): string[] {
  const properties = tool.args_schema?.properties
  if (!properties || typeof properties !== 'object') return []
  return Object.keys(properties)
}

async function loadAgentTools(): Promise<void> {
  toolsLoading.value = true
  toolsError.value = ''
  try {
    agentTools.value = await listAssistantTools()
  } catch (err: unknown) {
    toolsError.value = err instanceof Error ? err.message : '读取 Agent 工具失败'
  } finally {
    toolsLoading.value = false
  }
}

onMounted(loadAgentTools)
</script>

<template>
  <div class="assistant-settings-root">
    <h3 class="section-title">Agent 设置</h3>
    <p class="section-desc">
      配置通用 Agent 的高级能力，灵感助手与工作流 Agent 共享这些参数与模式。
    </p>

    <el-form label-width="160px" class="assistant-form" size="small">
      <!-- 参数配置组 -->
      <div class="group-title">参数设置</div>

      <el-form-item>
        <template #label>
          <span>
            采样温度 (temperature)
            <el-tooltip placement="top" effect="dark">
              <template #content>
                控制输出的随机性，数值越大越有创意、越发散，越小越保守、越稳定。<br/>
                建议范围 0.4 ~ 0.9。默认值为 0.6。
              </template>
              <el-icon class="field-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input-number
          v-model="assistantTemperature"
          :min="0.1"
          :max="2"
          :step="0.1"
          :precision="2"
          controls-position="right"
          placeholder="0.6"
        />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span>
            最大输出 Token 数
            <el-tooltip placement="top" effect="dark">
              <template #content>
                控制单次回复的最大长度。值越大，回复可以越长，但也会增加响应时间和费用。<br/>
                默认值为 -1（不限制）。
              </template>
              <el-icon class="field-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input-number
          v-model="assistantMaxTokens"
          :min="-1"
          :max="65536"
          :step="512"
          controls-position="right"
          placeholder="-1"
        />
      </el-form-item>

      <el-form-item>
        <template #label>
          <span>
            超时 (秒)
            <el-tooltip placement="top" effect="dark">
              <template #content>
                限制单次调用的最长等待时间，避免请求长时间挂起。<br/>
                默认值为 90 秒。
              </template>
              <el-icon class="field-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-input-number
          v-model="assistantTimeout"
          :min="10"
          :max="600"
          :step="10"
          controls-position="right"
          placeholder="90"
        />
      </el-form-item>

      <el-divider />

      <!-- React 配置组 -->
      <div class="group-title">模式设置</div>
      <el-form-item>
        <template #label>
          <span>
            React 模式
            <el-tooltip placement="top" effect="dark">
              <template #content>
                让模型通过文本协议输出工具调用指令（<Action>{...}</Action>），
                系统解析后真正调用工具，适合不支持函数调用的模型。
              </template>
              <el-icon class="field-help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-switch v-model="reactModeEnabled" />
      </el-form-item>
    </el-form>

    <el-divider />

    <div class="tools-section">
      <div class="tools-head">
        <div>
          <h4 class="tools-title">小说 Agent 可用工具</h4>
          <p class="tools-desc">
            当前项目中的灵感/小说 Agent 会从后端注册表获得这些工具。
          </p>
        </div>
        <div class="tools-actions">
          <el-tag size="small" effect="plain">{{ toolCountText }}</el-tag>
          <el-button size="small" :loading="toolsLoading" @click="loadAgentTools">刷新</el-button>
        </div>
      </div>

      <el-alert
        v-if="toolsError"
        class="tools-error"
        type="error"
        :title="toolsError"
        show-icon
        :closable="false"
      />

      <el-skeleton v-if="toolsLoading && !agentTools.length" :rows="4" animated />

      <el-empty
        v-else-if="!toolsError && !agentTools.length"
        description="暂无可用工具"
        :image-size="80"
      />

      <div v-else class="tool-list">
        <div v-for="tool in agentTools" :key="tool.name" class="tool-item">
          <div class="tool-item-head">
            <div class="tool-name-row">
              <span class="tool-name">{{ tool.name }}</span>
              <el-tag size="small" :type="riskTagType(tool.risk_level)" effect="plain">
                {{ formatRiskLevel(tool.risk_level) }}
              </el-tag>
              <el-tag v-if="tool.requires_confirmation" size="small" type="danger" effect="plain">
                需确认
              </el-tag>
            </div>
            <span class="tool-source">{{ tool.namespace }}</span>
          </div>
          <p class="tool-description">{{ tool.description || '无说明' }}</p>
          <div class="tool-params">
            <span class="param-label">参数</span>
            <template v-if="getToolParameterNames(tool).length">
              <el-tag
                v-for="param in getToolParameterNames(tool)"
                :key="`${tool.name}-${param}`"
                size="small"
                effect="plain"
              >
                {{ param }}
              </el-tag>
            </template>
            <span v-else class="empty-params">无参数</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assistant-settings-root {
  padding: 16px 12px 24px 12px;
}

.section-title {
  margin: 0 0 4px 0;
  font-size: 15px;
  font-weight: 600;
}

.section-desc {
  margin: 0 0 16px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.assistant-form {
  max-width: 520px;
}

.field-hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.hint-alert {
  margin-top: 12px;
}

.group-title {
  margin: 8px 0 4px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.field-help-icon {
  margin-left: 4px;
  cursor: help;
}

.tools-section {
  max-width: 860px;
}

.tools-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.tools-title {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
}

.tools-desc {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tools-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.tools-error {
  margin-bottom: 12px;
}

.tool-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}

.tool-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 10px 12px;
  background: var(--el-fill-color-blank);
}

.tool-item-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}

.tool-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.tool-name {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.tool-source {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tool-description {
  margin: 8px 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
}

.tool-params {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.param-label,
.empty-params {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
