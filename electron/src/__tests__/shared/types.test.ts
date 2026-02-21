import { describe, it, expect } from 'vitest'
import type {
  AudioChunkMessage,
  ControlMessage,
  PartialTranscriptMessage,
  FinalTranscriptMessage,
  StatusMessage,
  SummaryMessage,
  CaptureConfig,
  Session,
  TranscriptEntry,
  WordTimestamp,
} from '../../shared/types'

// Type-level tests — verify object shapes satisfy their interfaces
describe('Shared Types', () => {
  describe('AudioChunkMessage', () => {
    it('has the correct shape', () => {
      const msg: AudioChunkMessage = {
        type: 'audio_chunk',
        data: 'base64encodeddata',
        timestamp: Date.now(),
        session_id: 'test-session',
      }
      expect(msg.type).toBe('audio_chunk')
      expect(typeof msg.data).toBe('string')
      expect(typeof msg.timestamp).toBe('number')
      expect(typeof msg.session_id).toBe('string')
    })
  })

  describe('ControlMessage', () => {
    it('supports start action', () => {
      const msg: ControlMessage = {
        type: 'control',
        action: 'start',
        session_id: 'test-session',
      }
      expect(msg.action).toBe('start')
    })

    it('supports stop action', () => {
      const msg: ControlMessage = {
        type: 'control',
        action: 'stop',
        session_id: 'test-session',
      }
      expect(msg.action).toBe('stop')
    })

    it('accepts optional config', () => {
      const config: CaptureConfig = {
        source: 'microphone',
        language: 'en',
        model: 'parakeet',
        enable_diarization: true,
      }
      const msg: ControlMessage = {
        type: 'control',
        action: 'start',
        session_id: 'test-session',
        config,
      }
      expect(msg.config).toEqual(config)
    })
  })

  describe('PartialTranscriptMessage', () => {
    it('has the correct shape', () => {
      const msg: PartialTranscriptMessage = {
        type: 'partial_transcript',
        text: 'Hello wor',
        chunk_id: 1,
        confidence: 0.85,
        timestamp_ms: 1000,
      }
      expect(msg.type).toBe('partial_transcript')
      expect(msg.confidence).toBeGreaterThanOrEqual(0)
      expect(msg.confidence).toBeLessThanOrEqual(1)
    })
  })

  describe('FinalTranscriptMessage', () => {
    it('has required fields', () => {
      const msg: FinalTranscriptMessage = {
        type: 'final_transcript',
        text: 'Hello world',
        chunk_id: 1,
        confidence: 0.95,
        start_ms: 0,
        end_ms: 1500,
      }
      expect(msg.type).toBe('final_transcript')
      expect(msg.end_ms).toBeGreaterThan(msg.start_ms)
    })

    it('accepts optional speaker and words', () => {
      const words: WordTimestamp[] = [
        { word: 'Hello', start_ms: 0, end_ms: 500, confidence: 0.98 },
        { word: 'world', start_ms: 600, end_ms: 1200, confidence: 0.95 },
      ]
      const msg: FinalTranscriptMessage = {
        type: 'final_transcript',
        text: 'Hello world',
        chunk_id: 1,
        confidence: 0.96,
        speaker: 'SPEAKER_00',
        start_ms: 0,
        end_ms: 1500,
        words,
      }
      expect(msg.speaker).toBe('SPEAKER_00')
      expect(msg.words).toHaveLength(2)
    })
  })

  describe('StatusMessage', () => {
    it('reflects backend states', () => {
      const states: StatusMessage['state'][] = ['ready', 'transcribing', 'paused', 'error']
      states.forEach((state) => {
        const msg: StatusMessage = {
          type: 'status',
          state,
          model_loaded: true,
          gpu_available: false,
        }
        expect(msg.state).toBe(state)
      })
    })
  })

  describe('Session', () => {
    it('has the correct shape', () => {
      const session: Session = {
        id: 'uuid-123',
        title: 'Team standup',
        created_at: 1700000000000,
        updated_at: 1700001000000,
        duration_ms: 1800000,
        transcript_count: 42,
      }
      expect(session.id).toBe('uuid-123')
      expect(session.duration_ms).toBe(1800000)
    })

    it('accepts optional summary', () => {
      const session: Session = {
        id: 'uuid-456',
        title: 'Planning',
        created_at: Date.now(),
        updated_at: Date.now(),
        duration_ms: 3600000,
        transcript_count: 120,
        summary: 'We discussed the roadmap.',
      }
      expect(session.summary).toBeDefined()
    })
  })

  describe('CaptureConfig', () => {
    it('supports all capture sources', () => {
      const sources: CaptureConfig['source'][] = ['system', 'microphone', 'both']
      sources.forEach((source) => {
        const config: CaptureConfig = {
          source,
          language: 'en',
          model: 'parakeet',
          enable_diarization: false,
        }
        expect(config.source).toBe(source)
      })
    })
  })
})
