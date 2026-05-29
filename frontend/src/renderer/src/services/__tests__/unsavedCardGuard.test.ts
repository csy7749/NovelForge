import { strict as assert } from 'node:assert'
import {
  createUnsavedCardGuard,
  type UnsavedCardDecision,
} from '../unsavedCardGuard'

async function run(): Promise<void> {
  await testAllowsNavigationWhenNothingIsDirty()
  await testSavesDirtyCardsBeforeNavigation()
  await testDiscardsDirtyCardsWithoutSaving()
  await testCancelsNavigationWhenUserCancels()
}

async function testAllowsNavigationWhenNothingIsDirty(): Promise<void> {
  const guard = createUnsavedCardGuard()
  let prompted = false

  const canLeave = await guard.confirmLeave(async () => {
    prompted = true
    return 'cancel'
  })

  assert.equal(canLeave, true)
  assert.equal(prompted, false)
}

async function testSavesDirtyCardsBeforeNavigation(): Promise<void> {
  const guard = createUnsavedCardGuard()
  let saved = false

  guard.register({
    cardId: 1,
    title: '角色卡',
    isDirty: () => true,
    save: async () => {
      saved = true
    },
  })

  const decisions: UnsavedCardDecision[] = []
  const canLeave = await guard.confirmLeave(async (entries) => {
    decisions.push(entries.length === 1 ? 'save' : 'cancel')
    return 'save'
  })

  assert.equal(canLeave, true)
  assert.deepEqual(decisions, ['save'])
  assert.equal(saved, true)
}

async function testDiscardsDirtyCardsWithoutSaving(): Promise<void> {
  const guard = createUnsavedCardGuard()
  let saved = false

  guard.register({
    cardId: 3,
    title: '设定卡',
    isDirty: () => true,
    save: async () => {
      saved = true
    },
  })

  const canLeave = await guard.confirmLeave(async () => 'discard')

  assert.equal(canLeave, true)
  assert.equal(saved, false)
}

async function testCancelsNavigationWhenUserCancels(): Promise<void> {
  const guard = createUnsavedCardGuard()
  let saved = false

  guard.register({
    cardId: 2,
    title: '章节正文',
    isDirty: () => true,
    save: async () => {
      saved = true
    },
  })

  const canLeave = await guard.confirmLeave(async () => 'cancel')

  assert.equal(canLeave, false)
  assert.equal(saved, false)
}

run().catch((error) => {
  console.error(error)
  process.exit(1)
})
