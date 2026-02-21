import WebSocket from 'ws'
import { ServerMessage, CaptureConfig } from '../../shared/types'

type MessageHandler = (msg: ServerMessage) => void

/**
 * TranscriptionClient manages the WebSocket connection to the Python backend.
 *
 * It handles:
 * - Connecting and disconnecting from the backend
 * - Sending audio chunks and control messages
 * - Receiving and dispatching server messages (transcripts, status, summaries)
 * - Automatic reconnection on unexpected disconnection (up to maxReconnectAttempts)
 */
export class TranscriptionClient {
  private ws: WebSocket | null = null
  private messageHandlers: MessageHandler[] = []
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 3

  constructor(private url: string = 'ws://127.0.0.1:8765/ws/transcribe') {}

  /**
   * Open a WebSocket connection to the backend.
   * Resolves when the connection is established; rejects on error or timeout.
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url)
      const timeout = setTimeout(() => reject(new Error('Connection timeout')), 10_000)

      this.ws.on('open', () => {
        clearTimeout(timeout)
        this.reconnectAttempts = 0
        resolve()
      })

      this.ws.on('error', (err) => {
        clearTimeout(timeout)
        reject(err)
      })

      this.ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data.toString()) as ServerMessage
          this.messageHandlers.forEach((h) => h(msg))
        } catch {
          console.warn('[WsClient] Failed to parse message')
        }
      })

      this.ws.on('close', () => {
        // Attempt exponential-ish reconnect unless we've been explicitly disconnected
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          const delay = 2000 * this.reconnectAttempts
          console.warn(`[WsClient] Connection closed. Reconnect attempt ${this.reconnectAttempts} in ${delay}ms`)
          setTimeout(() => this.connect().catch(console.error), delay)
        }
      })
    })
  }

  /**
   * Register a handler for server-sent messages.
   * Returns an unsubscribe function.
   */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler)
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler)
    }
  }

  /**
   * Send a raw PCM audio chunk (as a Buffer) to the backend.
   * The buffer is base64-encoded before transmission.
   *
   * @param buffer    - Raw audio bytes (PCM 16-bit, 16kHz, mono)
   * @param sessionId - Optional session identifier (defaults to 'default')
   */
  sendAudioChunk(buffer: Buffer, sessionId?: string): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    const msg = {
      type: 'audio_chunk',
      data: buffer.toString('base64'),
      timestamp: Date.now(),
      session_id: sessionId ?? 'default',
    }
    this.ws.send(JSON.stringify(msg))
  }

  /**
   * Send a control message to the backend (start/stop/pause/resume).
   *
   * @param action    - The control action to perform
   * @param config    - Optional capture config (used with 'start')
   * @param sessionId - Optional session identifier (defaults to 'default')
   */
  sendControl(
    action: 'start' | 'stop' | 'pause' | 'resume',
    config?: Partial<CaptureConfig>,
    sessionId?: string,
  ): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    const msg = {
      type: 'control',
      action,
      session_id: sessionId ?? 'default',
      config,
    }
    this.ws.send(JSON.stringify(msg))
  }

  /**
   * Close the WebSocket connection and prevent auto-reconnect.
   */
  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts // prevent auto-reconnect
    this.ws?.close()
    this.ws = null
  }

  /** Returns true if the WebSocket is currently open. */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
