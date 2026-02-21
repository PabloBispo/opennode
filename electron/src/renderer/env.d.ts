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

  // Cleanup
  removeAllListeners: (channel: string) => void
}

declare global {
  interface Window {
    opennode: OpenNodeAPI
  }
}
