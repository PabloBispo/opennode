import { globalShortcut } from 'electron'
import ElectronStore from 'electron-store'
import { AppSettings } from '../../shared/types'

// ─── Defaults ─────────────────────────────────────────────────────────────────

const DEFAULT_SETTINGS: AppSettings = {
  asr_engine: 'parakeet',
  language: 'auto',
  enable_diarization: true,
  max_speakers: 10,
  enable_summarization: true,
  summarization_provider: 'ollama',
  ollama_model: 'llama3.2',
  capture_source: 'system',
  overlay_position: 'top-right',
  overlay_opacity: 0.85,
  theme: 'system',
}

// ─── SettingsService ──────────────────────────────────────────────────────────

/**
 * SettingsService wraps electron-store to provide typed read/write access to
 * application settings. It also handles global shortcut registration and
 * syncing relevant settings to the Python backend.
 */
class SettingsService {
  private store: ElectronStore<AppSettings>

  constructor() {
    this.store = new ElectronStore<AppSettings>({
      name: 'settings',
      defaults: DEFAULT_SETTINGS,
    })
  }

  /**
   * Return the full settings object from the persistent store.
   */
  get(): AppSettings {
    // electron-store's .store getter returns the whole record
    return this.store.store as AppSettings
  }

  /**
   * Merge a partial update into the stored settings and return the result.
   */
  update(partial: Partial<AppSettings>): AppSettings {
    for (const [key, value] of Object.entries(partial)) {
      this.store.set(key as keyof AppSettings, value as AppSettings[keyof AppSettings])
    }
    return this.get()
  }

  /**
   * Clear all stored settings, reverting to defaults.
   */
  reset(): AppSettings {
    this.store.clear()
    return this.get()
  }

  /**
   * Register global keyboard shortcuts.
   * All existing shortcuts are unregistered first to avoid duplicates.
   *
   * @param handlers - Callback functions for each shortcut action.
   */
  registerShortcuts(handlers: {
    toggleRecording?: () => void
    toggleOverlay?: () => void
    togglePause?: () => void
  }): void {
    globalShortcut.unregisterAll()

    if (handlers.toggleRecording) {
      globalShortcut.register('CommandOrControl+Shift+R', handlers.toggleRecording)
    }

    if (handlers.toggleOverlay) {
      globalShortcut.register('CommandOrControl+Shift+O', handlers.toggleOverlay)
    }

    if (handlers.togglePause) {
      globalShortcut.register('CommandOrControl+Shift+P', handlers.togglePause)
    }
  }

  /**
   * Push the ASR/transcription-relevant settings to the Python backend.
   * This is fire-and-forget — failures are silently ignored so a missing
   * backend does not crash the Electron process.
   *
   * @param port - The port the FastAPI backend listens on (default 8765).
   */
  syncToBackend(port: number = 8765): void {
    const settings = this.get()
    fetch(`http://127.0.0.1:${port}/api/config`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asr_engine: settings.asr_engine,
        language: settings.language,
        enable_diarization: settings.enable_diarization,
        enable_summarization: settings.enable_summarization,
      }),
    }).catch(() => {}) // ignore if backend is not running
  }
}

export const settingsService = new SettingsService()
export type { AppSettings }
