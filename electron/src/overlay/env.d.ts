/// <reference types="vite/client" />

/**
 * The restricted API surface exposed to the overlay window via the overlay preload script.
 * Use `(window.opennode as OverlayAPI)` in overlay components.
 */
export interface OverlayAPI {
  onPartialTranscript: (cb: (data: { text: string; chunk_id: number; confidence: number; timestamp_ms: number }) => void) => void
  onFinalTranscript: (cb: (data: { text: string; chunk_id: number; confidence: number; speaker?: string; start_ms: number; end_ms: number }) => void) => void
  onStatus: (cb: (data: { state: string; model_loaded: boolean; gpu_available: boolean }) => void) => void
  setClickThrough: (enabled: boolean) => void
  drag: (deltaX: number, deltaY: number) => void
  minimize: () => void
  close: () => void
  removeAllListeners: (channel: string) => void
}
