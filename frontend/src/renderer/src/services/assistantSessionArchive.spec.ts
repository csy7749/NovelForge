import {
  buildAssistantSessionArchive,
  mergeAssistantSessions,
  parseAssistantSessionArchive,
} from './assistantSessionArchive'

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(message)
}

function assertThrows(fn: () => unknown, message: string): void {
  let thrown = false
  try {
    fn()
  } catch {
    thrown = true
  }
  assert(thrown, message)
}

const baseSession = {
  id: 'session-a',
  projectId: 7,
  title: '第一段灵感',
  createdAt: 100,
  updatedAt: 200,
  messages: [{ role: 'user' as const, content: '写一个开场' }],
}

const archive = buildAssistantSessionArchive({
  projectId: 7,
  sessions: [baseSession],
  exportedAt: 300,
})

assert(archive.schemaVersion === 1, 'archive schema version should be stable')
assert(archive.projectId === 7, 'archive should keep project id')
assert(archive.sessions.length === 1, 'archive should keep sessions')

const parsed = parseAssistantSessionArchive(JSON.stringify(archive))
assert(parsed.sessions[0]?.id === 'session-a', 'parser should restore session id')
assertThrows(
  () => parseAssistantSessionArchive('{"schemaVersion":2,"projectId":7,"sessions":[]}'),
  'parser should reject unsupported versions',
)

const merged = mergeAssistantSessions([
  { ...baseSession, updatedAt: 100 },
], [
  { ...baseSession, updatedAt: 500, title: '更新后的灵感' },
  { ...baseSession, id: 'session-b', updatedAt: 250 },
])

assert(merged.length === 2, 'merge should dedupe by id and keep new sessions')
assert(merged[0]?.title === '更新后的灵感', 'merge should keep newest duplicate session')
