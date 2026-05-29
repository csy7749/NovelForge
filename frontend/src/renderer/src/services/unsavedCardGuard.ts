export type UnsavedCardDecision = 'save' | 'discard' | 'cancel'

export interface UnsavedCardEntry {
  cardId: number
  title: string
  isDirty: () => boolean
  save: () => Promise<void>
}

export type UnsavedCardPrompt = (entries: readonly UnsavedCardEntry[]) => Promise<UnsavedCardDecision>

export interface UnsavedCardGuard {
  register: (entry: UnsavedCardEntry) => () => void
  getDirtyEntries: () => UnsavedCardEntry[]
  confirmLeave: (prompt: UnsavedCardPrompt) => Promise<boolean>
}

export function createUnsavedCardGuard(): UnsavedCardGuard {
  const entries = new Map<number, UnsavedCardEntry>()

  function register(entry: UnsavedCardEntry): () => void {
    entries.set(entry.cardId, entry)
    return () => {
      const current = entries.get(entry.cardId)
      if (current === entry) entries.delete(entry.cardId)
    }
  }

  function getDirtyEntries(): UnsavedCardEntry[] {
    return Array.from(entries.values()).filter((entry) => entry.isDirty())
  }

  async function confirmLeave(prompt: UnsavedCardPrompt): Promise<boolean> {
    const dirtyEntries = getDirtyEntries()
    if (dirtyEntries.length === 0) return true

    const decision = await prompt(dirtyEntries)
    if (decision === 'discard') return true
    if (decision === 'cancel') return false

    for (const entry of dirtyEntries) {
      await entry.save()
    }
    return true
  }

  return {
    register,
    getDirtyEntries,
    confirmLeave,
  }
}

export const unsavedCardGuard = createUnsavedCardGuard()
