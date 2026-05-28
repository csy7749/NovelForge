import { ElectronAPI } from '@electron-toolkit/preload'

interface Api {
  setApiKey: (id: number, apiKey: string) => Promise<{ success: boolean; error?: string }>
  getApiKey: (id: number) => Promise<{ success: boolean; apiKey?: string; error?: string }>
  openIdeasHome: () => Promise<{ success: boolean }>
  exportAssistantHistory: (payload: {
    filename: string
    content: string
  }) => Promise<{ success: boolean; filePath?: string; error?: string }>
}

declare global {
  interface Window {
    electron: ElectronAPI
    api: Api
  }
}
