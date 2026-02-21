import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('opennode', {
  onPartialTranscript: (cb: (data: { text: string; chunk_id: number; confidence: number; timestamp_ms: number }) => void) =>
    ipcRenderer.on('transcript:partial', (_, data) => cb(data)),
  onFinalTranscript: (cb: (data: { text: string; chunk_id: number; confidence: number; speaker?: string; start_ms: number; end_ms: number }) => void) =>
    ipcRenderer.on('transcript:final', (_, data) => cb(data)),
  onStatus: (cb: (data: { state: string; model_loaded: boolean; gpu_available: boolean }) => void) =>
    ipcRenderer.on('status', (_, data) => cb(data)),
  setClickThrough: (enabled: boolean) =>
    ipcRenderer.send('overlay:click-through', enabled),
  drag: (deltaX: number, deltaY: number) =>
    ipcRenderer.send('overlay:drag', { deltaX, deltaY }),
  minimize: () => ipcRenderer.send('overlay:minimize'),
  close: () => ipcRenderer.send('overlay:close'),
  removeAllListeners: (channel: string) => ipcRenderer.removeAllListeners(channel),
})
