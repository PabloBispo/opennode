import { describe, it, expect, beforeEach } from 'vitest'
import { useStore } from '../../renderer/store'

describe('AppStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useStore.setState({
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
    })
  })

  describe('initial state', () => {
    it('starts with idle recording state', () => {
      expect(useStore.getState().recordingState).toBe('idle')
    })

    it('starts with zero elapsed time', () => {
      expect(useStore.getState().elapsedMs).toBe(0)
    })

    it('starts with empty transcripts', () => {
      expect(useStore.getState().transcripts).toEqual([])
    })

    it('starts on dashboard view', () => {
      expect(useStore.getState().currentView).toBe('dashboard')
    })

    it('starts with backend status starting', () => {
      expect(useStore.getState().backendStatus).toBe('starting')
    })
  })

  describe('recording state actions', () => {
    it('setRecordingState updates state', () => {
      useStore.getState().setRecordingState('recording')
      expect(useStore.getState().recordingState).toBe('recording')
    })

    it('can transition through states', () => {
      const { setRecordingState } = useStore.getState()
      setRecordingState('recording')
      expect(useStore.getState().recordingState).toBe('recording')
      setRecordingState('paused')
      expect(useStore.getState().recordingState).toBe('paused')
      setRecordingState('idle')
      expect(useStore.getState().recordingState).toBe('idle')
    })
  })

  describe('transcript actions', () => {
    const mockLine = {
      id: 'test-1',
      text: 'Hello world',
      speaker: 'SPEAKER_00',
      isPartial: false,
      startMs: 0,
      confidence: 0.95,
    }

    it('addTranscript appends a transcript line', () => {
      useStore.getState().addTranscript(mockLine)
      expect(useStore.getState().transcripts).toHaveLength(1)
      expect(useStore.getState().transcripts[0]).toEqual(mockLine)
    })

    it('addTranscript clears partial text', () => {
      useStore.getState().setPartialText('partial...')
      useStore.getState().addTranscript(mockLine)
      expect(useStore.getState().partialText).toBe('')
    })

    it('setPartialText updates partial text', () => {
      useStore.getState().setPartialText('transcribing...')
      expect(useStore.getState().partialText).toBe('transcribing...')
    })

    it('clearTranscripts removes all transcripts and partial text', () => {
      useStore.getState().addTranscript(mockLine)
      useStore.getState().setPartialText('partial...')
      useStore.getState().clearTranscripts()
      expect(useStore.getState().transcripts).toEqual([])
      expect(useStore.getState().partialText).toBe('')
    })

    it('accumulates multiple transcripts', () => {
      const lines = [
        { ...mockLine, id: '1', text: 'First' },
        { ...mockLine, id: '2', text: 'Second' },
        { ...mockLine, id: '3', text: 'Third' },
      ]
      lines.forEach((l) => useStore.getState().addTranscript(l))
      expect(useStore.getState().transcripts).toHaveLength(3)
    })
  })

  describe('session actions', () => {
    const mockSessions = [
      {
        id: 'sess-1',
        title: 'Meeting 1',
        created_at: Date.now(),
        updated_at: Date.now(),
        duration_ms: 60000,
        transcript_count: 10,
      },
    ]

    it('setSessions updates sessions list', () => {
      useStore.getState().setSessions(mockSessions)
      expect(useStore.getState().sessions).toEqual(mockSessions)
    })

    it('setSelectedSession updates selected session ID', () => {
      useStore.getState().setSelectedSession('sess-1')
      expect(useStore.getState().selectedSessionId).toBe('sess-1')
    })

    it('setSelectedSession can be cleared with null', () => {
      useStore.getState().setSelectedSession('sess-1')
      useStore.getState().setSelectedSession(null)
      expect(useStore.getState().selectedSessionId).toBeNull()
    })
  })

  describe('backend status actions', () => {
    it('setBackendStatus updates status', () => {
      useStore.getState().setBackendStatus('ready')
      expect(useStore.getState().backendStatus).toBe('ready')
    })

    it('setModelLoaded updates model loaded state', () => {
      useStore.getState().setModelLoaded(true)
      expect(useStore.getState().modelLoaded).toBe(true)
    })

    it('setGpuAvailable updates GPU availability', () => {
      useStore.getState().setGpuAvailable(true)
      expect(useStore.getState().gpuAvailable).toBe(true)
    })
  })

  describe('navigation actions', () => {
    it('setCurrentView navigates to live', () => {
      useStore.getState().setCurrentView('live')
      expect(useStore.getState().currentView).toBe('live')
    })

    it('setCurrentView navigates to settings', () => {
      useStore.getState().setCurrentView('settings')
      expect(useStore.getState().currentView).toBe('settings')
    })

    it('setCurrentView navigates to session', () => {
      useStore.getState().setCurrentView('session')
      expect(useStore.getState().currentView).toBe('session')
    })
  })

  describe('elapsed timer actions', () => {
    it('tickElapsed increments by 1000ms', () => {
      useStore.getState().tickElapsed()
      expect(useStore.getState().elapsedMs).toBe(1000)
    })

    it('tickElapsed accumulates correctly', () => {
      const { tickElapsed } = useStore.getState()
      tickElapsed()
      tickElapsed()
      tickElapsed()
      expect(useStore.getState().elapsedMs).toBe(3000)
    })

    it('resetElapsed resets to zero', () => {
      useStore.getState().tickElapsed()
      useStore.getState().tickElapsed()
      useStore.getState().resetElapsed()
      expect(useStore.getState().elapsedMs).toBe(0)
    })
  })
})
