// ─── WebSocket Protocol Types ────────────────────────────────────────────────

export interface AudioChunkMessage {
  type: 'audio_chunk'
  data: string // base64 PCM 16-bit 16kHz mono
  timestamp: number
  session_id: string
}

export interface ControlMessage {
  type: 'control'
  action: 'start' | 'stop' | 'pause' | 'resume'
  session_id: string
  config?: CaptureConfig
}

export interface PartialTranscriptMessage {
  type: 'partial_transcript'
  text: string
  chunk_id: number
  confidence: number
  timestamp_ms: number
}

export interface FinalTranscriptMessage {
  type: 'final_transcript'
  text: string
  chunk_id: number
  confidence: number
  speaker?: string
  start_ms: number
  end_ms: number
  words?: WordTimestamp[]
}

export interface StatusMessage {
  type: 'status'
  state: 'ready' | 'transcribing' | 'paused' | 'error'
  model_loaded: boolean
  gpu_available: boolean
  error?: string
}

export interface SummaryMessage {
  type: 'summary'
  session_id: string
  summary: string
  action_items: string[]
  key_decisions: string[]
}

export type ServerMessage =
  | PartialTranscriptMessage
  | FinalTranscriptMessage
  | StatusMessage
  | SummaryMessage

export type ClientMessage = AudioChunkMessage | ControlMessage

// ─── App Types ───────────────────────────────────────────────────────────────

export interface WordTimestamp {
  word: string
  start_ms: number
  end_ms: number
  confidence: number
}

export interface CaptureConfig {
  source: 'system' | 'microphone' | 'both'
  language: string
  model: 'parakeet' | 'whisper'
  enable_diarization: boolean
}

export interface Session {
  id: string
  title: string
  created_at: number
  updated_at: number
  duration_ms: number
  transcript_count: number
  summary?: string
}

export interface TranscriptEntry {
  id: string
  session_id: string
  text: string
  speaker?: string
  start_ms: number
  end_ms: number
  confidence: number
  is_final: boolean
}

export interface AppSettings {
  asr_engine: 'parakeet' | 'whisper' | 'onnx'
  language: string
  enable_diarization: boolean
  max_speakers: number
  enable_summarization: boolean
  summarization_provider: 'ollama' | 'api'
  ollama_model: string
  capture_source: 'system' | 'microphone' | 'both'
  overlay_position: 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left'
  overlay_opacity: number
  theme: 'system' | 'light' | 'dark'
}

export interface SystemInfo {
  gpu_available: boolean
  gpu_name?: string
  gpu_vram_mb?: number
  platform: string
  arch: string
  total_ram_mb: number
}
