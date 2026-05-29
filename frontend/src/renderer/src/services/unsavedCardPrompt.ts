import { ElMessage, ElMessageBox } from 'element-plus'
import {
  unsavedCardGuard,
  type UnsavedCardDecision,
  type UnsavedCardEntry,
} from './unsavedCardGuard'

const MAX_DISPLAYED_CARDS = 5

function formatDirtyCardList(entries: readonly UnsavedCardEntry[]): string {
  const visibleTitles = entries.slice(0, MAX_DISPLAYED_CARDS).map((entry) => `「${entry.title}」`)
  const remainingCount = entries.length - visibleTitles.length
  const suffix =
    remainingCount > 0 ? `${visibleTitles.join('、')} 等 ${entries.length} 张卡片` : visibleTitles.join('、')
  return suffix || '当前卡片'
}

async function promptUnsavedCards(entries: readonly UnsavedCardEntry[]): Promise<UnsavedCardDecision> {
  try {
    await ElMessageBox.confirm(
      `${formatDirtyCardList(entries)} 有未保存修改。离开前要保存吗？关闭此提示会留在当前页面。`,
      '未保存的卡片',
      {
        type: 'warning',
        confirmButtonText: '保存后离开',
        cancelButtonText: '暂不保存并离开',
        distinguishCancelAndClose: true,
        showClose: true,
        showCancelButton: true,
      }
    )
    return 'save'
  } catch (action) {
    if (action === 'cancel') return 'discard'
    return 'cancel'
  }
}

export async function confirmLeaveWithUnsavedCards(): Promise<boolean> {
  try {
    return await unsavedCardGuard.confirmLeave(promptUnsavedCards)
  } catch (error) {
    console.error('保存未完成，已取消离开:', error)
    ElMessage.error('保存失败，已留在当前页面')
    return false
  }
}

export function hasUnsavedCards(): boolean {
  return unsavedCardGuard.getDirtyEntries().length > 0
}
