import { contextBridge, ipcRenderer } from 'electron'
import type {
  CaptureConfig,
  AppSettings,
  Session,
  SystemInfo,
  PartialTranscriptMessage,
  FinalTranscriptMessage,
  StatusMessage,
} from '@shared/types'

/**
 * The OpenNode preload API is exposed on window.opennode in the renderer.
 * All communication with the main process goes through contextBridge so that
 * renderer code runs in a sandboxed context without direct Node.js access.
 */
const opennodeAPI = {
  // ─── Audio capture ──────────────────────────────────────────────────────────
  /** Start audio capture with the given config. */
  startCapture: (config: CaptureConfig): Promise<{ ok: boolean }> =>
    ipcRenderer.invoke('audio:start', config),

  /** Stop the active audio capture. */
  stopCapture: (): Promise<{ ok: boolean }> => ipcRenderer.invoke('audio:stop'),

  /**
   * Send a raw PCM audio chunk from the renderer (mic capture) to the main
   * process, which forwards it to the Python backend via WebSocket.
   *
   * @param buffer - ArrayBuffer containing PCM int16 samples (16kHz, mono)
   */
  sendAudioChunk: (buffer: ArrayBuffer): void => ipcRenderer.send('audio:send-chunk', buffer),

  /**
   * Register a callback invoked when the main process asks the renderer to
   * start microphone capture.
   */
  onStartMic: (cb: (config: import('@shared/types').CaptureConfig) => void): void => {
    ipcRenderer.on('audio:start-mic', (_event, config: import('@shared/types').CaptureConfig) => cb(config))
  },

  /**
   * Register a callback invoked when the main process asks the renderer to
   * stop microphone capture.
   */
  onStopMic: (cb: () => void): void => {
    ipcRenderer.on('audio:stop-mic', () => cb())
  },

  // ─── Transcription events ───────────────────────────────────────────────────
  /** Register a callback for partial (in-progress) transcript events. */
  onPartialTranscript: (cb: (data: PartialTranscriptMessage) => void): void => {
    ipcRenderer.on('transcript:partial', (_event, data: PartialTranscriptMessage) => cb(data))
  },

  /** Register a callback for final transcript events. */
  onFinalTranscript: (cb: (data: FinalTranscriptMessage) => void): void => {
    ipcRenderer.on('transcript:final', (_event, data: FinalTranscriptMessage) => cb(data))
  },

  /** Register a callback for backend status updates. */
  onStatus: (cb: (data: StatusMessage) => void): void => {
    ipcRenderer.on('status', (_event, data: StatusMessage) => cb(data))
  },

  // ─── Sessions ───────────────────────────────────────────────────────────────
  /** Fetch the list of all recorded sessions. */
  getSessions: (): Promise<Session[]> => ipcRenderer.invoke('sessions:list'),

  /** Fetch a single session by ID. */
  getSession: (id: string): Promise<Session | undefined> =>
    ipcRenderer.invoke('sessions:get', id),

  /** Delete a session by ID. */
  deleteSession: (id: string): Promise<{ ok: boolean }> =>
    ipcRenderer.invoke('sessions:delete', id),

  // ─── Settings ───────────────────────────────────────────────────────────────
  /** Retrieve persisted application settings. */
  getSettings: (): Promise<AppSettings> => ipcRenderer.invoke('settings:get'),

  /** Persist a partial settings update (merged with existing settings). */
  updateSettings: (settings: Partial<AppSettings>): Promise<AppSettings> =>
    ipcRenderer.invoke('settings:update', settings),

  // ─── Overlay ────────────────────────────────────────────────────────────────
  /** Toggle the PiP overlay window visibility. */
  toggleOverlay: (): Promise<{ visible: boolean }> => ipcRenderer.invoke('overlay:toggle'),

  // ─── System ─────────────────────────────────────────────────────────────────
  /** Retrieve system information (GPU, RAM, platform). */
  getSystemInfo: (): Promise<SystemInfo> => ipcRenderer.invoke('app:system-info'),

  // ─── Backend management ──────────────────────────────────────────────────────
  /** Register a callback for when the Python backend becomes ready. */
  onBackendReady: (cb: (port: number) => void): void => {
    ipcRenderer.on('backend:ready', (_event, port: number) => cb(port))
  },

  /** Register a callback for backend log lines. */
  onBackendLog: (cb: (lines: string[]) => void): void => {
    ipcRenderer.on('backend:log', (_event, lines: string[]) => cb(lines))
  },

  /** Get the current backend process status. */
  getBackendStatus: (): Promise<{ running: boolean; ready: boolean; port: number; pid: number | null }> =>
    ipcRenderer.invoke('backend:status'),

  /** Get all buffered backend log lines. */
  getBackendLogs: (): Promise<string[]> => ipcRenderer.invoke('backend:logs'),

  /** Restart the Python backend process. */
  restartBackend: (): Promise<{ running: boolean; ready: boolean; port: number; pid: number | null }> =>
    ipcRenderer.invoke('backend:restart'),

  // ─── Cleanup ─────────────────────────────────────────────────────────────────
  /**
   * Remove all IPC listeners for the given channel.
   * Call this in React useEffect cleanup to avoid duplicate listeners.
   */
  removeAllListeners: (channel: string): void => {
    ipcRenderer.removeAllListeners(channel)
  },
}

contextBridge.exposeInMainWorld('opennode', opennodeAPI)
