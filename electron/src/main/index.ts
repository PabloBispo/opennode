import { app, ipcMain } from 'electron'
import os from 'os'
import ElectronStore from 'electron-store'
import { WindowManager } from './WindowManager'
import { settingsService } from './services/settings'
import { backendManager } from './services/backend-manager'
import { TranscriptionClient } from './services/ws-client'
import { AudioCaptureService } from './services/audio-capture'
import { systemTray } from './tray'
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

// ─── WebSocket client ─────────────────────────────────────────────────────────

const wsClient = new TranscriptionClient()

/**
 * Attempt to connect to the Python backend WebSocket.
 * This is best-effort — errors are swallowed so a missing backend does not
 * crash the Electron process.
 */
async function connectToBackend(): Promise<void> {
  try {
    await wsClient.connect()
    console.log('[main] Connected to backend WebSocket')

    // Forward server messages to the renderer and overlay
    wsClient.onMessage((msg) => {
      const mainWindow = windowManager.getMainWindow()
      const overlayWindow = windowManager.getOverlayWindow()

      const sendToMain = (channel: string, data: unknown) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send(channel, data)
        }
      }

      const sendToOverlay = (channel: string, data: unknown) => {
        if (overlayWindow && !overlayWindow.isDestroyed() && overlayWindow.isVisible()) {
          overlayWindow.webContents.send(channel, data)
        }
      }

      switch (msg.type) {
        case 'partial_transcript':
          sendToMain('transcript:partial', msg)
          sendToOverlay('transcript:partial', msg)
          break
        case 'final_transcript':
          sendToMain('transcript:final', msg)
          sendToOverlay('transcript:final', msg)
          break
        case 'status':
          sendToMain('status', msg)
          sendToOverlay('status', msg)
          break
        case 'summary':
          sendToMain('summary', msg)
          break
        default:
          break
      }
    })
  } catch (err) {
    console.warn('[main] Could not connect to backend WebSocket:', err)
  }
}

// ─── Audio capture service ────────────────────────────────────────────────────

const audioCaptureService = new AudioCaptureService(() => wsClient)

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

/**
 * Start audio capture.
 * Checks permissions, then delegates to AudioCaptureService which handles
 * both system loopback and mic capture (via renderer IPC).
 */
ipcMain.handle('audio:start', async (_event, config: CaptureConfig) => {
  console.log('[main] audio:start', config)
  await audioCaptureService.checkPermissions()
  const mainWindow = windowManager.getMainWindow()
  await audioCaptureService.start(config, mainWindow)
  return { ok: true }
})

/**
 * Stop audio capture.
 */
ipcMain.handle('audio:stop', async () => {
  console.log('[main] audio:stop')
  const mainWindow = windowManager.getMainWindow()
  await audioCaptureService.stop(mainWindow)
  return { ok: true }
})

/**
 * Receive raw PCM audio chunks from the renderer (mic capture via AudioWorklet)
 * and forward them to the Python backend via WebSocket.
 */
ipcMain.on('audio:send-chunk', (_event, buffer: ArrayBuffer) => {
  if (wsClient.isConnected) {
    wsClient.sendAudioChunk(Buffer.from(buffer))
  }
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

ipcMain.on('overlay:click-through', (_, enabled: boolean) => {
  const overlay = windowManager.getOverlayWindow()
  overlay?.setIgnoreMouseEvents(enabled, { forward: true })
})

ipcMain.on('overlay:drag', (_, { deltaX, deltaY }: { deltaX: number; deltaY: number }) => {
  const overlay = windowManager.getOverlayWindow()
  if (overlay) {
    const [x, y] = overlay.getPosition()
    overlay.setPosition(x + deltaX, y + deltaY)
  }
})

ipcMain.on('overlay:minimize', () => {
  // handled in renderer — just close
})

ipcMain.on('overlay:close', () => {
  const overlay = windowManager.getOverlayWindow()
  overlay?.hide()
})

// ─── System info ──────────────────────────────────────────────────────────────

ipcMain.handle('app:system-info', async (): Promise<SystemInfo> => {
  const totalRam = Math.round(os.totalmem() / (1024 * 1024))
  const envStatus = await backendManager.checkEnvironment()
  return {
    gpu_available: envStatus.gpuAvailable,
    gpu_name: envStatus.gpuName ?? undefined,
    platform: process.platform,
    arch: process.arch,
    total_ram_mb: totalRam,
  }
})

// ─── Backend management ───────────────────────────────────────────────────────

ipcMain.handle('backend:status', async () => {
  return backendManager.getStatus()
})

ipcMain.handle('backend:logs', async () => {
  return backendManager.logs
})

ipcMain.handle('backend:restart', async () => {
  await backendManager.stop()
  await backendManager.start()
  return backendManager.getStatus()
})

// ─── Tray ─────────────────────────────────────────────────────────────────────

ipcMain.on('tray:set-state', (_, state: 'idle' | 'recording' | 'paused') => {
  systemTray.setState(state)
})

// ─── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  const mainWindow = windowManager.createMainWindow()

  // ─── System tray ───────────────────────────────────────────────────────────

  systemTray.create({
    onToggleRecording: () => {
      // Toggle recording — send to renderer or handle directly
      mainWindow?.webContents.send('tray:toggle-recording')
    },
    onToggleOverlay: () => {
      windowManager.toggleOverlay()
      systemTray.setOverlayVisible(!windowManager.getOverlayWindow()?.isVisible())
    },
    onShowMainWindow: () => {
      if (mainWindow) {
        mainWindow.show()
        mainWindow.focus()
      }
    },
  })

  // ─── Backend events ────────────────────────────────────────────────────────

  backendManager.on('ready', (port: number) => {
    console.log(`[main] Python backend ready on port ${port}`)
    mainWindow?.webContents.send('backend:ready', port)
    // Connect WebSocket once backend is confirmed ready
    connectToBackend().catch(console.error)
  })

  backendManager.on('error', (message: string) => {
    console.error('[main] Python backend error:', message)
    mainWindow?.webContents.send('backend:error', message)
  })

  backendManager.on('log', (lines: string[]) => {
    mainWindow?.webContents.send('backend:log', lines)
  })

  backendManager.on('restarting', (info: { attempt: number; delay: number }) => {
    console.log(`[main] Python backend restarting (attempt ${info.attempt}, delay ${info.delay}ms)`)
  })

  backendManager.on('stopped', (code: number | null) => {
    console.log(`[main] Python backend stopped with code ${code}`)
  })

  // Start Python backend (non-blocking — ready event fires when up)
  backendManager.start().catch((err: unknown) => {
    console.error('[main] Failed to start Python backend:', err)
    // Fall back to attempting direct WebSocket connection (backend may already be running)
    connectToBackend().catch(console.error)
  })

  // Register global shortcuts.
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

// Keep running in tray — don't quit when all windows are closed.
// User must quit via tray menu or Cmd+Q.
app.on('window-all-closed', () => {
  // intentionally empty — tray keeps the app alive
})

// Clean up WebSocket, Python backend, and tray on quit
app.on('before-quit', () => {
  systemTray.destroy()
  wsClient.disconnect()
  backendManager.stop().catch((err: unknown) => {
    console.error('[main] Error stopping Python backend:', err)
  })
})
