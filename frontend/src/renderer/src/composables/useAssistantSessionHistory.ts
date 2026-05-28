import { ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import type { AssistantChatSession, AssistantPanelMessage } from '@renderer/types/assistantPanel'
import {
  buildAssistantSessionArchive,
  buildAssistantSessionArchiveFilename,
  mergeAssistantSessions,
  parseAssistantSessionArchive,
} from '@renderer/services/assistantSessionArchive'

interface UseAssistantSessionHistoryOptions {
  projectId: Ref<number | null | undefined>
  projectName?: Ref<string | null | undefined>
  messages: Ref<AssistantPanelMessage[]>
  currentSession?: Ref<AssistantChatSession>
  historySessions?: Ref<AssistantChatSession[]>
  historyDrawerVisible?: Ref<boolean>
  onScrollToBottom?: () => void
}

interface AssistantSessionHistoryController {
  currentSession: Ref<AssistantChatSession>
  historySessions: Ref<AssistantChatSession[]>
  historyDrawerVisible: Ref<boolean>
  saveCurrentSession: () => void
  createNewSession: () => void
  loadSession: (sessionId: string) => void
  handleDeleteSession: (sessionId: string) => void
  formatSessionTime: (timestamp: number) => string
  exportHistorySessions: () => Promise<void>
  importHistorySessionsFromFile: (file: File) => Promise<void>
}

function createEmptySession(projectId: number): AssistantChatSession {
  return {
    id: `session_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`,
    projectId,
    title: '新对话',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  }
}

function getSessionStorageKey(projectId: number): string {
  return `assistant-sessions-${projectId}`
}

function getActiveSessionStorageKey(projectId: number): string {
  return `assistant-active-session-${projectId}`
}

function dedupeSessionsById(sessions: AssistantChatSession[]): AssistantChatSession[] {
  const seen = new Set<string>()
  const result: AssistantChatSession[] = []
  for (const item of sessions) {
    if (!item?.id || seen.has(item.id)) continue
    seen.add(item.id)
    result.push(item)
  }
  return result
}

function downloadTextFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function assertExportSuccess(result: { success: boolean; filePath?: string; error?: string }): string {
  if (result.success && result.filePath) return result.filePath
  throw new Error(result.error || '导出历史对话失败')
}

export function useAssistantSessionHistory(
  options: UseAssistantSessionHistoryOptions,
): AssistantSessionHistoryController {
  const currentSession = options.currentSession ?? ref<AssistantChatSession>(createEmptySession(options.projectId.value || 0))
  const historySessions = options.historySessions ?? ref<AssistantChatSession[]>([])
  const historyDrawerVisible = options.historyDrawerVisible ?? ref(false)

  function readActiveSessionId(projectId: number): string | null {
    try {
      return localStorage.getItem(getActiveSessionStorageKey(projectId))
    } catch {
      return null
    }
  }

  function writeActiveSessionId(projectId: number, sessionId: string | null): void {
    try {
      const key = getActiveSessionStorageKey(projectId)
      if (!sessionId) {
        localStorage.removeItem(key)
        return
      }
      localStorage.setItem(key, sessionId)
    } catch {
      // ignore storage errors
    }
  }

  function loadHistorySessions(projectId: number): void {
    try {
      const key = getSessionStorageKey(projectId)
      const stored = localStorage.getItem(key)
      if (!stored) {
        historySessions.value = []
        return
      }
      const sessions = dedupeSessionsById(JSON.parse(stored) as AssistantChatSession[])
        .sort((a, b) => b.updatedAt - a.updatedAt)
      historySessions.value = sessions
      localStorage.setItem(key, JSON.stringify(sessions))
    } catch {
      historySessions.value = []
    }
  }

  function saveCurrentSession(): void {
    const projectId = options.projectId.value
    if (!projectId) return
    if (options.messages.value.length === 0) return

    try {
      const sessionToSave: AssistantChatSession = {
        ...currentSession.value,
        messages: JSON.parse(JSON.stringify(options.messages.value)),
        updatedAt: Date.now(),
        projectId,
      }

      if (sessionToSave.title === '新对话') {
        const firstUserMessage = options.messages.value.find(item => item.role === 'user')
        if (firstUserMessage) {
          sessionToSave.title =
            firstUserMessage.content.substring(0, 20) +
            (firstUserMessage.content.length > 20 ? '...' : '')
        }
      }

      const key = getSessionStorageKey(projectId)
      const stored = localStorage.getItem(key)
      const sessions = dedupeSessionsById(stored ? (JSON.parse(stored) as AssistantChatSession[]) : []).filter(
        session => session.id !== sessionToSave.id,
      )
      sessions.unshift(sessionToSave)

      if (sessions.length > 50) {
        sessions.splice(50)
      }

      localStorage.setItem(key, JSON.stringify(sessions))
      historySessions.value = sessions
      writeActiveSessionId(projectId, sessionToSave.id)

      if (currentSession.value.title !== sessionToSave.title) {
        currentSession.value.title = sessionToSave.title
      }
    } catch {
      // keep current UI state on localStorage failure
    }
  }

  function createNewSession(): void {
    if (options.messages.value.length > 0) {
      saveCurrentSession()
    }

    currentSession.value = createEmptySession(options.projectId.value || 0)
    options.messages.value = []
    historyDrawerVisible.value = false
    if (options.projectId.value) {
      writeActiveSessionId(options.projectId.value, currentSession.value.id)
    }
  }

  function loadSession(sessionId: string): void {
    if (sessionId === currentSession.value.id) return

    const session = historySessions.value.find(item => item.id === sessionId)
    if (!session) return

    if (options.messages.value.length > 0) {
      saveCurrentSession()
    }

    currentSession.value = { ...session }
    options.messages.value = [...session.messages]
    historyDrawerVisible.value = false
    options.onScrollToBottom?.()
    if (options.projectId.value) {
      writeActiveSessionId(options.projectId.value, currentSession.value.id)
    }
  }

  function deleteSession(sessionId: string): void {
    const projectId = options.projectId.value
    if (!projectId) return

    try {
      const key = getSessionStorageKey(projectId)
      historySessions.value = historySessions.value.filter(item => item.id !== sessionId)
      localStorage.setItem(key, JSON.stringify(historySessions.value))

      if (currentSession.value.id === sessionId) {
        const fallback = historySessions.value[0]
        if (fallback) {
          currentSession.value = { ...fallback }
          options.messages.value = [...fallback.messages]
          writeActiveSessionId(projectId, fallback.id)
        } else {
          currentSession.value = createEmptySession(projectId)
          options.messages.value = []
          writeActiveSessionId(projectId, currentSession.value.id)
        }
      } else {
        writeActiveSessionId(projectId, currentSession.value.id)
      }

      ElMessage.success('已删除会话')
    } catch {
      ElMessage.error('删除会话失败')
    }
  }

  function handleDeleteSession(sessionId: string): void {
    ElMessageBox.confirm('确定要删除这个对话吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => {
        deleteSession(sessionId)
      })
      .catch(() => {
        // user canceled
      })
  }

  function formatSessionTime(timestamp: number): string {
    const now = Date.now()
    const diff = now - timestamp
    const minute = 60 * 1000
    const hour = 60 * minute
    const day = 24 * hour

    if (diff < minute) return '刚刚'
    if (diff < hour) return `${Math.floor(diff / minute)}分钟前`
    if (diff < day) return `${Math.floor(diff / hour)}小时前`
    if (diff < 7 * day) return `${Math.floor(diff / day)}天前`

    const date = new Date(timestamp)
    return `${date.getMonth() + 1}/${date.getDate()}`
  }

  function activateSessionAfterImport(projectId: number, sessions: AssistantChatSession[]): void {
    const activeSessionId = readActiveSessionId(projectId)
    const targetSession = activeSessionId
      ? (sessions.find(item => item.id === activeSessionId) || sessions[0])
      : sessions[0]

    if (!targetSession) {
      currentSession.value = createEmptySession(projectId)
      options.messages.value = []
      writeActiveSessionId(projectId, currentSession.value.id)
      return
    }

    currentSession.value = { ...targetSession }
    options.messages.value = [...targetSession.messages]
    writeActiveSessionId(projectId, targetSession.id)
    options.onScrollToBottom?.()
  }

  async function confirmProjectMismatch(archiveProjectId: number, currentProjectId: number): Promise<void> {
    if (archiveProjectId === currentProjectId) return
    await ElMessageBox.confirm(
      `导入文件来自项目 ${archiveProjectId}，当前项目是 ${currentProjectId}。继续导入会把这些会话归入当前项目。`,
      '确认导入',
      {
        confirmButtonText: '继续导入',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  }

  async function exportHistorySessions(): Promise<void> {
    const projectId = options.projectId.value
    if (!projectId) {
      ElMessage.error('请先打开项目再导出历史对话')
      return
    }

    saveCurrentSession()
    if (historySessions.value.length === 0) {
      ElMessage.warning('暂无可导出的历史对话')
      return
    }

    const archive = buildAssistantSessionArchive({ projectId, sessions: historySessions.value })
    const filename = buildAssistantSessionArchiveFilename({
      projectId,
      projectName: options.projectName?.value,
      timestamp: archive.exportedAt,
    })
    const content = JSON.stringify(archive, null, 2)

    if (window.api?.exportAssistantHistory) {
      const filePath = assertExportSuccess(await window.api.exportAssistantHistory({ filename, content }))
      ElMessage.success(`已导出到 ${filePath}`)
      return
    }

    downloadTextFile(filename, content)
    ElMessage.success('已下载历史对话 JSON，可提交到 git 同步')
  }

  async function importHistorySessionsFromFile(file: File): Promise<void> {
    const projectId = options.projectId.value
    if (!projectId) throw new Error('请先打开项目再导入历史对话')

    const archive = parseAssistantSessionArchive(await file.text())
    await confirmProjectMismatch(archive.projectId, projectId)
    saveCurrentSession()

    const importedSessions = archive.sessions.map(session => ({ ...session, projectId }))
    const mergedSessions = mergeAssistantSessions(historySessions.value, importedSessions)
    const key = getSessionStorageKey(projectId)

    localStorage.setItem(key, JSON.stringify(mergedSessions))
    historySessions.value = mergedSessions
    activateSessionAfterImport(projectId, mergedSessions)
    ElMessage.success(`已导入 ${archive.sessions.length} 个历史对话`)
  }

  watch(
    () => options.projectId.value,
    newProjectId => {
      if (!newProjectId) return
      loadHistorySessions(newProjectId)
      if (historySessions.value.length > 0) {
        const activeSessionId = readActiveSessionId(newProjectId)
        const targetSession = activeSessionId
          ? (historySessions.value.find(item => item.id === activeSessionId) || historySessions.value[0])
          : historySessions.value[0]

        currentSession.value = { ...targetSession }
        options.messages.value = [...targetSession.messages]
        writeActiveSessionId(newProjectId, targetSession.id)
        options.onScrollToBottom?.()
        return
      }

      currentSession.value = createEmptySession(newProjectId)
      options.messages.value = []
      writeActiveSessionId(newProjectId, currentSession.value.id)
    },
    { immediate: true },
  )

  return {
    currentSession,
    historySessions,
    historyDrawerVisible,
    saveCurrentSession,
    createNewSession,
    loadSession,
    handleDeleteSession,
    formatSessionTime,
    exportHistorySessions,
    importHistorySessionsFromFile,
  }
}
