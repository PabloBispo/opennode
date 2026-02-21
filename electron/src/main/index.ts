import { app, ipcMain } from 'electron'
import os from 'os'
import ElectronStore from 'electron-store'
import { WindowManager } from './WindowManager'
import type { AppSettings, CaptureConfig, Session, SystemInfo } from '@shared/types'

// ─── Store (persistent settings) ─────────────────────────────────────────────

const DEFAULT_SETTINGS: AppSettings = {
  asr_engine: 'parakeet',
  language: 'en',
  enable_diarization: false,
  max_speakers: 4,
  enable_summarization: false,
  summarization_provider: 'ollama',
  ollama_model: 'llama3',
  capture_source: 'microphone',
  overlay_position: 'bottom-right',
  overlay_opacity: 0.9,
  theme: 'system',
}

const store = new ElectronStore<{ settings: AppSettings; sessions: Session[] }>({
  defaults: {
    settings: DEFAULT_SETTINGS,
    sessions: [],
  },
})

// ─── Window management ────────────────────────────────────────────────────────

const windowManager = new WindowManager()

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

/**
 * Audio capture — actual implementation lives in Task 10/11.
 * Stubs are provided here so the renderer can call these channels safely.
 */
ipcMain.handle('audio:start', async (_event, config: CaptureConfig) => {
  console.log('[main] audio:start', config)
  // TODO (Task 10): forward to Python backend via WebSocket
  return { ok: true }
})

ipcMain.handle('audio:stop', async () => {
  console.log('[main] audio:stop')
  // TODO (Task 10): stop audio pipeline
  return { ok: true }
})

// ─── Sessions ─────────────────────────────────────────────────────────────────

ipcMain.handle('sessions:list', async (): Promise<Session[]> => {
  return store.get('sessions', [])
})

ipcMain.handle('sessions:get', async (_event, id: string): Promise<Session | undefined> => {
  const sessions: Session[] = store.get('sessions', [])
  return sessions.find((s) => s.id === id)
})

ipcMain.handle('sessions:delete', async (_event, id: string): Promise<{ ok: boolean }> => {
  const sessions: Session[] = store.get('sessions', [])
  store.set(
    'sessions',
    sessions.filter((s) => s.id !== id),
  )
  return { ok: true }
})

// ─── Settings ─────────────────────────────────────────────────────────────────

ipcMain.handle('settings:get', async (): Promise<AppSettings> => {
  return store.get('settings', DEFAULT_SETTINGS)
})

ipcMain.handle('settings:update', async (_event, partial: Partial<AppSettings>): Promise<AppSettings> => {
  const current = store.get('settings', DEFAULT_SETTINGS)
  const updated = { ...current, ...partial }
  store.set('settings', updated)
  return updated
})

// ─── Overlay ──────────────────────────────────────────────────────────────────

ipcMain.handle('overlay:toggle', async (): Promise<{ visible: boolean }> => {
  windowManager.toggleOverlay()
  const overlay = windowManager.getOverlayWindow()
  return { visible: overlay?.isVisible() ?? false }
})

// ─── System info ──────────────────────────────────────────────────────────────

ipcMain.handle('app:system-info', async (): Promise<SystemInfo> => {
  const totalRam = Math.round(os.totalmem() / (1024 * 1024))
  return {
    gpu_available: false, // TODO (Task 09): query Python backend for GPU info
    platform: process.platform,
    arch: process.arch,
    total_ram_mb: totalRam,
  }
})

// ─── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  windowManager.createMainWindow()

  // macOS: re-create window when dock icon is clicked and no windows exist
  app.on('activate', () => {
    if (windowManager.getMainWindow() === null) {
      windowManager.createMainWindow()
    }
  })
})

// Quit the app when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
