import { app, ipcMain } from 'electron'
import os from 'os'
import ElectronStore from 'electron-store'
import { WindowManager } from './WindowManager'
import { settingsService } from './services/settings'
import type { CaptureConfig, Session, SystemInfo } from '@shared/types'

// ─── Store (session persistence only) ────────────────────────────────────────
// Settings are now managed by settingsService (electron-store under the hood).

const store = new ElectronStore<{ sessions: Session[] }>({
  name: 'sessions',
  defaults: {
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

ipcMain.handle('settings:get', async () => {
  return settingsService.get()
})

ipcMain.handle('settings:update', async (_event, partial: Parameters<typeof settingsService.update>[0]) => {
  const updated = settingsService.update(partial)
  // Propagate changes to the Python backend asynchronously
  settingsService.syncToBackend()
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

  // Register global shortcuts. Handlers are stubs here — Tasks 10/11 will wire
  // the recording pipeline. The overlay toggle calls the windowManager directly.
  settingsService.registerShortcuts({
    toggleRecording: () => {
      console.log('[main] global shortcut: toggleRecording')
    },
    toggleOverlay: () => {
      windowManager.toggleOverlay()
    },
    togglePause: () => {
      console.log('[main] global shortcut: togglePause')
    },
  })

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
