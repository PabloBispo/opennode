import { create } from 'zustand'
import type { Session } from '@shared/types'

interface TranscriptLine {
  id: string
  text: string
  speaker?: string
  isPartial: boolean
  startMs: number
  confidence: number
}

type BackendStatus = 'starting' | 'ready' | 'error' | 'offline'
type RecordingState = 'idle' | 'recording' | 'paused'

interface AppStore {
  // Recording
  recordingState: RecordingState
  elapsedMs: number
  currentSessionId: string | null
  transcripts: TranscriptLine[]
  partialText: string

  // Sessions
  sessions: Session[]
  selectedSessionId: string | null

  // Backend
  backendStatus: BackendStatus
  modelLoaded: boolean
  gpuAvailable: boolean

  // Navigation
  currentView: 'dashboard' | 'live' | 'session' | 'settings'

  // Actions
  setRecordingState: (state: RecordingState) => void
  addTranscript: (line: TranscriptLine) => void
  setPartialText: (text: string) => void
  clearTranscripts: () => void
  setSessions: (sessions: Session[]) => void
  setSelectedSession: (id: string | null) => void
  setBackendStatus: (status: BackendStatus) => void
  setModelLoaded: (loaded: boolean) => void
  setGpuAvailable: (available: boolean) => void
  setCurrentView: (view: AppStore['currentView']) => void
  tickElapsed: () => void
  resetElapsed: () => void
}

export const useStore = create<AppStore>((set) => ({
  recordingState: 'idle',
  elapsedMs: 0,
  currentSessionId: null,
  transcripts: [],
  partialText: '',
  sessions: [],
  selectedSessionId: null,
  backendStatus: 'starting',
  modelLoaded: false,
  gpuAvailable: false,
  currentView: 'dashboard',

  setRecordingState: (recordingState) => set({ recordingState }),
  addTranscript: (line) => set((s) => ({ transcripts: [...s.transcripts, line], partialText: '' })),
  setPartialText: (partialText) => set({ partialText }),
  clearTranscripts: () => set({ transcripts: [], partialText: '' }),
  setSessions: (sessions) => set({ sessions }),
  setSelectedSession: (selectedSessionId) => set({ selectedSessionId }),
  setBackendStatus: (backendStatus) => set({ backendStatus }),
  setModelLoaded: (modelLoaded) => set({ modelLoaded }),
  setGpuAvailable: (gpuAvailable) => set({ gpuAvailable }),
  setCurrentView: (currentView) => set({ currentView }),
  tickElapsed: () => set((s) => ({ elapsedMs: s.elapsedMs + 1000 })),
  resetElapsed: () => set({ elapsedMs: 0 }),
}))

export type { TranscriptLine, BackendStatus, RecordingState }
