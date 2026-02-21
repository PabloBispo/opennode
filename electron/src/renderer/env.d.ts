/// <reference types="vite/client" />

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
 * The OpenNode API surface exposed by the preload script via contextBridge.
 * Available as window.opennode in all renderer contexts.
 */
interface OpenNodeAPI {
  // Audio
  startCapture: (config: CaptureConfig) => Promise<{ ok: boolean }>
  stopCapture: () => Promise<{ ok: boolean }>
  /** Send a raw PCM audio chunk from the renderer to the main process. */
  sendAudioChunk: (buffer: ArrayBuffer) => void
  /** Listen for the main process signal to start mic capture. */
  onStartMic: (cb: (config: CaptureConfig) => void) => void
  /** Listen for the main process signal to stop mic capture. */
  onStopMic: (cb: () => void) => void

  // Transcription events
  onPartialTranscript: (cb: (data: PartialTranscriptMessage) => void) => void
  onFinalTranscript: (cb: (data: FinalTranscriptMessage) => void) => void
  onStatus: (cb: (data: StatusMessage) => void) => void

  // Sessions
  getSessions: () => Promise<Session[]>
  getSession: (id: string) => Promise<Session | undefined>
  deleteSession: (id: string) => Promise<{ ok: boolean }>

  // Settings
  getSettings: () => Promise<AppSettings>
  updateSettings: (settings: Partial<AppSettings>) => Promise<AppSettings>

  // Overlay
  toggleOverlay: () => Promise<{ visible: boolean }>

  // System
  getSystemInfo: () => Promise<SystemInfo>

  // Backend management
  onBackendReady: (cb: (port: number) => void) => void
  onBackendLog: (cb: (lines: string[]) => void) => void
  getBackendStatus: () => Promise<{ running: boolean; ready: boolean; port: number; pid: number | null }>
  getBackendLogs: () => Promise<string[]>
  restartBackend: () => Promise<{ running: boolean; ready: boolean; port: number; pid: number | null }>

  // Cleanup
  removeAllListeners: (channel: string) => void
}

declare global {
  interface Window {
    opennode: OpenNodeAPI
  }
}
