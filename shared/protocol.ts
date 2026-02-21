// Shared WebSocket protocol types — used by both Electron frontend and any external client.
// Python equivalents are in backend/opennode/protocol.py

export type {
  AudioChunkMessage,
  ControlMessage,
  PartialTranscriptMessage,
  FinalTranscriptMessage,
  StatusMessage,
  SummaryMessage,
  ServerMessage,
  ClientMessage,
  WordTimestamp,
  CaptureConfig,
  Session,
  TranscriptEntry,
  AppSettings,
  SystemInfo,
} from '../electron/src/shared/types'
