import type {
  TraceRunRead,
  TraceSourceRead,
  TraceSpanRead,
  TraceStepRead
} from '@renderer/api/aiTraces'

export interface TraceSourceView {
  id: string
  label: string
  preview: string
  sourceType: string
  clickable: boolean
  jumpTarget: Record<string, unknown> | null
  spans: TraceSpanRead[]
}

export interface TraceStepView {
  id: string
  title: string
  description: string
  status: string
  statusLabel: string
  kindLabel: string
  timeLabel: string
  inputPreview: string
  outputPreview: string
  error: string
  sources: TraceSourceView[]
  spanSnippets: Array<{ id: string; text: string; sourceLabel: string }>
}

export interface TraceRunView {
  id: string
  title: string
  status: string
  statusLabel: string
  startedAt: string
  steps: TraceStepView[]
}

const STATUS_LABELS: Record<string, string> = {
  running: '进行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
  skipped: '已跳过'
}

const KIND_LABELS: Record<string, string> = {
  tool: '工具',
  pipeline: '管线',
  context: '上下文',
  generation: '生成',
  review: '审核',
  model: '模型',
  error: '错误'
}

const ENTRYPOINT_LABELS: Record<string, string> = {
  assistant_chat: '灵感助手',
  workflow_agent_chat: 'Workflow Agent',
  continuation_generate: '正文续写',
  general_ai_generate: '结构化生成',
  chapter_review: '内容审核'
}

function unwrapSummary(summary: Record<string, unknown> | null | undefined): unknown {
  if (!summary) return null
  if (summary.type === 'object') return summary.value
  if (summary.type === 'text') return summary.preview
  if (summary.type === 'array') return summary.items
  return summary.value ?? summary.preview ?? summary
}

function getNestedValue(value: unknown, keys: string[]): string {
  if (!value || typeof value !== 'object') return ''
  const record = value as Record<string, unknown>
  for (const key of keys) {
    const raw = record[key]
    if (raw !== undefined && raw !== null && String(raw).trim()) return String(raw)
  }
  return ''
}

function compactJson(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function sourceClickable(source: TraceSourceRead): boolean {
  const target = source.jump_target || {}
  return target.type === 'card' && target.card_id !== undefined
}

function buildToolDescription(step: TraceStepRead): string {
  const input = unwrapSummary(step.input_summary)
  if (step.name === 'create_card') {
    const type = getNestedValue(input, ['card_type', 'card_type_name', 'type'])
    const title = getNestedValue(input, ['title', 'name'])
    return `正在创建卡片${type ? `：类型=${type}` : ''}${title ? `，标题=${title}` : ''}`
  }
  return `${KIND_LABELS[step.kind] || '步骤'}：${step.name}`
}

function buildSources(step: TraceStepRead): TraceSourceView[] {
  return (step.sources || []).map((source) => ({
    id: source.id,
    label: source.label || source.source_ref || source.source_type,
    preview: source.preview || '未提供预览',
    sourceType: source.source_type,
    clickable: sourceClickable(source),
    jumpTarget: source.jump_target || null,
    spans: source.spans || []
  }))
}

function buildSpanSnippets(
  sources: TraceSourceView[]
): Array<{ id: string; text: string; sourceLabel: string }> {
  return sources.flatMap((source) =>
    source.spans.map((span) => ({
      id: span.id,
      text: span.text || `${span.start_offset}-${span.end_offset}`,
      sourceLabel: source.label
    }))
  )
}

export function toTraceRunView(run: TraceRunRead): TraceRunView {
  const entrypoint = ENTRYPOINT_LABELS[run.entrypoint] || run.entrypoint
  return {
    id: run.id,
    title: `${entrypoint} · ${formatTime(run.started_at)}`,
    status: run.status,
    statusLabel: STATUS_LABELS[run.status] || run.status,
    startedAt: formatTime(run.started_at),
    steps: (run.steps || []).map(toTraceStepView)
  }
}

export function toTraceStepView(step: TraceStepRead): TraceStepView {
  const sources = buildSources(step)
  return {
    id: step.id,
    title: step.name,
    description:
      step.kind === 'tool'
        ? buildToolDescription(step)
        : `${KIND_LABELS[step.kind] || '步骤'}：${step.name}`,
    status: step.status,
    statusLabel: STATUS_LABELS[step.status] || step.status,
    kindLabel: KIND_LABELS[step.kind] || step.kind,
    timeLabel: formatTime(step.timestamp),
    inputPreview: compactJson(unwrapSummary(step.input_summary)),
    outputPreview: compactJson(unwrapSummary(step.output_summary)),
    error: step.error || '',
    sources,
    spanSnippets: buildSpanSnippets(sources)
  }
}
