import { BrowserWindow, systemPreferences } from 'electron'
import { CaptureConfig } from '../../shared/types'
import type { TranscriptionClient } from './ws-client'

/** Minimal interface for the optional electron-audio-loopback package. */
interface AudioLoopbackInstance {
  on(event: 'data', cb: (buf: Buffer) => void): void
  start(): Promise<void>
  stop(): void
}

interface AudioCaptureOptions {
  sampleRate: number
  channels: number
  bitDepth: number
}

/**
 * AudioCaptureService orchestrates audio capture from the microphone and/or
 * system audio (loopback).
 *
 * - Microphone capture is handled in the renderer process via the Web Audio API
 *   (AudioWorklet). The main process instructs the renderer to start/stop mic
 *   capture by sending IPC events.
 *
 * - System (loopback) audio capture is attempted via the optional
 *   `electron-audio-loopback` package. If the package is unavailable, system
 *   capture is gracefully disabled with a console warning.
 */
export class AudioCaptureService {
  private isCapturing = false
  private _loopback: AudioLoopbackInstance | null = null

  constructor(private getWsClient: () => TranscriptionClient | null) {}

  /**
   * Check and request microphone/screen recording permissions.
   * On macOS, triggers the system permission dialog for the microphone.
   * On Windows/Linux, permissions are not required so this always returns true.
   */
  async checkPermissions(): Promise<{ mic: boolean; screen: boolean }> {
    if (process.platform === 'darwin') {
      const mic = systemPreferences.getMediaAccessStatus('microphone') === 'granted'
      const screen = systemPreferences.getMediaAccessStatus('screen') === 'granted'

      if (!mic) {
        await systemPreferences.askForMediaAccess('microphone')
      }

      return { mic, screen }
    }

    // Windows/Linux — no explicit permission API available
    return { mic: true, screen: true }
  }

  /**
   * Start audio capture according to the provided config.
   *
   * - Sends a 'start' control message to the backend via WebSocket.
   * - For microphone capture, instructs the renderer to begin AudioWorklet capture.
   * - For system capture, attempts to start the loopback device.
   *
   * @param config     - Capture configuration (source, language, model, etc.)
   * @param mainWindow - The Electron main window (used to send IPC events to renderer)
   */
  async start(config: CaptureConfig, mainWindow: BrowserWindow | null): Promise<void> {
    if (this.isCapturing) return
    this.isCapturing = true

    const ws = this.getWsClient()

    // Notify the Python backend that recording is starting
    ws?.sendControl('start', config)

    if (config.source === 'microphone' || config.source === 'both') {
      // Instruct the renderer to start microphone capture via AudioWorklet
      mainWindow?.webContents.send('audio:start-mic', config)
    }

    if (config.source === 'system' || config.source === 'both') {
      await this._startSystemCapture(ws)
    }
  }

  /**
   * Stop all active audio capture.
   * Sends a 'stop' control message to the backend and stops the loopback device.
   * The renderer is responsible for stopping mic capture when it receives the
   * `audio:stop-mic` event (sent separately by the IPC handler in index.ts).
   */
  async stop(mainWindow: BrowserWindow | null): Promise<void> {
    if (!this.isCapturing) return
    this.isCapturing = false

    this._stopSystemCapture()

    const ws = this.getWsClient()
    ws?.sendControl('stop')

    // Instruct renderer to stop mic capture
    mainWindow?.webContents.send('audio:stop-mic')
  }

  /**
   * Attempt to start loopback (system audio) capture using the optional
   * `electron-audio-loopback` native module.
   *
   * If the module is not installed or fails to load, system capture is skipped
   * gracefully and a warning is logged.
   */
  private async _startSystemCapture(ws: TranscriptionClient | null): Promise<void> {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const mod = require('electron-audio-loopback') as {
        AudioLoopback: new (opts: AudioCaptureOptions) => AudioLoopbackInstance
      }
      this._loopback = new mod.AudioLoopback({ sampleRate: 16000, channels: 1, bitDepth: 16 })
      this._loopback.on('data', (buffer: Buffer) => {
        ws?.sendAudioChunk(buffer)
      })
      await this._loopback.start()
    } catch {
      // electron-audio-loopback not available — system capture gracefully disabled
      console.warn(
        '[AudioCapture] electron-audio-loopback not available; system audio capture disabled',
      )
    }
  }

  /** Stop the loopback device if it is running. */
  private _stopSystemCapture(): void {
    this._loopback?.stop()
    this._loopback = null
  }

  /** Whether audio capture is currently active. */
  get capturing(): boolean {
    return this.isCapturing
  }
}
