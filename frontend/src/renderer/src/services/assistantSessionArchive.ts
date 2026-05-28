import type { AssistantChatSession, AssistantPanelMessage } from '../types/assistantPanel'

const SCHEMA_VERSION = 1
const DEFAULT_FILE_PREFIX = 'novelforge-assistant-history'

export interface AssistantSessionArchive {
  schemaVersion: 1
  exportedAt: number
  projectId: number
  sessions: AssistantChatSession[]
}

interface BuildArchiveOptions {
  projectId: number
  sessions: AssistantChatSession[]
  exportedAt?: number
}

interface BuildFilenameOptions {
  projectId: number
  projectName?: string | null
  timestamp?: number
}

function sanitizeFilenameSegment(value: string): string {
  return value
    .trim()
    .split('')
    .map(char => (char.charCodeAt(0) < 32 ? '-' : char))
    .join('')
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertNumber(value: unknown, fieldName: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`导入文件格式错误：${fieldName} 必须是数字`)
  }
  return value
}

function assertString(value: unknown, fieldName: string): string {
  if (typeof value !== 'string') {
    throw new Error(`导入文件格式错误：${fieldName} 必须是字符串`)
  }
  return value
}

function parseMessage(value: unknown, index: number): AssistantPanelMessage {
  if (!isRecord(value)) throw new Error(`导入文件格式错误：messages[${index}] 必须是对象`)
  const role = value.role
  if (role !== 'user' && role !== 'assistant') {
    throw new Error(`导入文件格式错误：messages[${index}].role 无效`)
  }
  return {
    ...value,
    role,
    content: assertString(value.content, `messages[${index}].content`),
  } as AssistantPanelMessage
}

function parseSession(value: unknown, index: number): AssistantChatSession {
  if (!isRecord(value)) throw new Error(`导入文件格式错误：sessions[${index}] 必须是对象`)
  const messages = value.messages
  if (!Array.isArray(messages)) {
    throw new Error(`导入文件格式错误：sessions[${index}].messages 必须是数组`)
  }
  return {
    id: assertString(value.id, `sessions[${index}].id`),
    projectId: assertNumber(value.projectId, `sessions[${index}].projectId`),
    title: assertString(value.title, `sessions[${index}].title`),
    createdAt: assertNumber(value.createdAt, `sessions[${index}].createdAt`),
    updatedAt: assertNumber(value.updatedAt, `sessions[${index}].updatedAt`),
    messages: messages.map(parseMessage),
  }
}

export function buildAssistantSessionArchive(options: BuildArchiveOptions): AssistantSessionArchive {
  return {
    schemaVersion: SCHEMA_VERSION,
    exportedAt: options.exportedAt ?? Date.now(),
    projectId: options.projectId,
    sessions: options.sessions.map(session => ({
      ...session,
      messages: JSON.parse(JSON.stringify(session.messages)) as AssistantPanelMessage[],
    })),
  }
}

export function parseAssistantSessionArchive(rawText: string): AssistantSessionArchive {
  const parsed = JSON.parse(rawText) as unknown
  if (!isRecord(parsed)) throw new Error('导入文件格式错误：根节点必须是对象')
  if (parsed.schemaVersion !== SCHEMA_VERSION) {
    throw new Error(`导入文件版本不支持：${String(parsed.schemaVersion)}`)
  }
  const sessions = parsed.sessions
  if (!Array.isArray(sessions)) throw new Error('导入文件格式错误：sessions 必须是数组')
  return {
    schemaVersion: SCHEMA_VERSION,
    exportedAt: assertNumber(parsed.exportedAt, 'exportedAt'),
    projectId: assertNumber(parsed.projectId, 'projectId'),
    sessions: sessions.map(parseSession),
  }
}

export function mergeAssistantSessions(
  existingSessions: AssistantChatSession[],
  importedSessions: AssistantChatSession[],
): AssistantChatSession[] {
  const byId = new Map<string, AssistantChatSession>()
  for (const session of existingSessions) byId.set(session.id, session)
  for (const session of importedSessions) {
    const previous = byId.get(session.id)
    if (!previous || session.updatedAt >= previous.updatedAt) byId.set(session.id, session)
  }
  return Array.from(byId.values()).sort((a, b) => b.updatedAt - a.updatedAt)
}

export function buildAssistantSessionArchiveFilename(options: BuildFilenameOptions): string {
  const date = new Date(options.timestamp ?? Date.now()).toISOString().slice(0, 10)
  const projectName = options.projectName ? sanitizeFilenameSegment(options.projectName) : ''
  const projectPart = projectName ? `${projectName}-project-${options.projectId}` : `project-${options.projectId}`
  return `${DEFAULT_FILE_PREFIX}-${projectPart}-${date}.json`
}
