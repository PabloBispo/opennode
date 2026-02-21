import '@testing-library/jest-dom'

// Mock electron APIs that are exposed via preload
const mockOpenNode = {
  startCapture: vi.fn().mockResolvedValue(undefined),
  stopCapture: vi.fn().mockResolvedValue(undefined),
  getSessions: vi.fn().mockResolvedValue([]),
  getSession: vi.fn().mockResolvedValue(null),
  deleteSession: vi.fn().mockResolvedValue(undefined),
  getSettings: vi.fn().mockResolvedValue({}),
  updateSettings: vi.fn().mockResolvedValue(undefined),
  toggleOverlay: vi.fn().mockResolvedValue(undefined),
  getSystemInfo: vi.fn().mockResolvedValue({
    gpu_available: false,
    platform: 'test',
    arch: 'x64',
    total_ram_mb: 8192,
  }),
  sendAudioChunk: vi.fn(),
  getBackendStatus: vi.fn().mockResolvedValue({ status: 'ready' }),
  getBackendLogs: vi.fn().mockResolvedValue([]),
  restartBackend: vi.fn().mockResolvedValue(undefined),
  removeAllListeners: vi.fn(),
  onPartialTranscript: vi.fn().mockReturnValue(() => {}),
  onFinalTranscript: vi.fn().mockReturnValue(() => {}),
  onStatus: vi.fn().mockReturnValue(() => {}),
  onBackendReady: vi.fn().mockReturnValue(() => {}),
  onBackendLog: vi.fn().mockReturnValue(() => {}),
  onStartMic: vi.fn().mockReturnValue(() => {}),
  onStopMic: vi.fn().mockReturnValue(() => {}),
  onTrayToggleRecording: vi.fn().mockReturnValue(() => {}),
  setTrayState: vi.fn(),
}

Object.defineProperty(window, 'opennode', {
  value: mockOpenNode,
  writable: true,
})
