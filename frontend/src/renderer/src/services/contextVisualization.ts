import type { AssembleContextResponse, ContextTraceSource } from '@renderer/api/ai'
import type { CardRead } from '@renderer/api/cards'
import {
  resolveTemplateDetails,
  type ResolvedTemplateToken,
} from '@renderer/services/contextResolver'

export interface ContextVisualizationToken extends ResolvedTemplateToken {
  kind: string
  label: string
  preview: string
}

export interface ContextVisualizationSource {
  id: string
  kind: string
  label: string
  sourceRef?: string | null
  preview: string
  count: number
  truncated: boolean
  state: 'resolved' | 'missing' | 'error'
}

export interface ContextVisualizationModel {
  template: string
  finalText: string
  tokens: ContextVisualizationToken[]
  sources: ContextVisualizationSource[]
  emptySources: string[]
  errors: string[]
  status: 'ok' | 'partial' | 'empty' | 'error' | string
}

export interface BuildContextVisualizationOptions {
  template: string
  cards: CardRead[]
  currentCard?: CardRead
  assembledContext?: AssembleContextResponse | null
}

const PREVIEW_LIMIT = 220

function trimPreview(value: unknown): string {
  const text = String(value || '').trim()
  if (text.length <= PREVIEW_LIMIT) return text
  return `${text.slice(0, PREVIEW_LIMIT)}...`
}

function classifyToken(token: string): { kind: string; label: string } {
  if (token.startsWith('facts.')) return { kind: 'facts', label: '事实结构' }
  if (token.startsWith('kg:')) return { kind: 'kg', label: '知识图谱' }
  if (token.startsWith('type:')) return { kind: 'card_reference', label: '类型卡片引用' }
  if (token.startsWith('self')) return { kind: 'card_reference', label: '当前卡片' }
  if (token.startsWith('parent')) return { kind: 'card_reference', label: '父级卡片' }
  if (token.startsWith('stage:')) return { kind: 'card_reference', label: '当前阶段' }
  if (token.startsWith('chapters:')) return { kind: 'card_reference', label: '章节集合' }
  return { kind: 'card_reference', label: '卡片引用' }
}

function tokenToSource(item: ContextVisualizationToken, index: number): ContextVisualizationSource {
  const isError = item.value.trim().startsWith('[Error:')
  return {
    id: `token:${index}:${item.start}`,
    kind: item.kind,
    label: `@${item.token}`,
    sourceRef: item.token,
    preview: trimPreview(item.value),
    count: item.resolved ? 1 : 0,
    truncated: false,
    state: isError ? 'error' : item.resolved ? 'resolved' : 'missing',
  }
}

function backendTraceToSource(item: ContextTraceSource, index: number): ContextVisualizationSource {
  return {
    id: `trace:${index}:${item.kind}:${item.source_ref || ''}`,
    kind: item.kind,
    label: item.label,
    sourceRef: item.source_ref,
    preview: trimPreview(item.preview),
    count: item.count,
    truncated: item.truncated,
    state: 'resolved',
  }
}

function decorateToken(item: ResolvedTemplateToken): ContextVisualizationToken {
  const meta = classifyToken(item.token)
  return {
    ...item,
    ...meta,
    preview: trimPreview(item.value),
  }
}

function collectErrors(tokens: ContextVisualizationToken[], backendErrors: string[]): string[] {
  const tokenErrors = tokens
    .filter(item => !item.resolved)
    .map(item => `未解析 token：@${item.token}`)
  return [...backendErrors, ...tokenErrors]
}

export function buildContextVisualizationModel(
  options: BuildContextVisualizationOptions
): ContextVisualizationModel {
  const details = resolveTemplateDetails({
    template: options.template,
    cards: options.cards,
    currentCard: options.currentCard,
    assembledContext: options.assembledContext,
  })
  const tokens = details.tokens.map(decorateToken)
  const tokenSources = tokens.map(tokenToSource)
  const trace = options.assembledContext?.trace
  const traceSources = (trace?.sources || []).map(backendTraceToSource)
  const errors = collectErrors(tokens, trace?.errors || [])
  const status = errors.length ? (traceSources.length ? 'partial' : 'error') : trace?.status || 'ok'
  return {
    template: details.template,
    finalText: details.result,
    tokens,
    sources: [...tokenSources, ...traceSources],
    emptySources: trace?.empty_sources || [],
    errors,
    status,
  }
}
