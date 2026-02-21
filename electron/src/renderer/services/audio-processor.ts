/**
 * MicAudioProcessor — captures microphone audio in the renderer process.
 *
 * Uses the Web Audio API (AudioWorklet) to capture microphone input and
 * convert it from float32 to PCM int16 (16kHz, mono) in 100ms chunks.
 * Each chunk is delivered via the `onChunk` callback so it can be forwarded
 * to the main process and then to the Python backend.
 */

const BUFFER_SIZE = 1600 // 100ms at 16kHz
const SAMPLE_RATE = 16000

export class MicAudioProcessor {
  private audioContext: AudioContext | null = null
  private workletNode: AudioWorkletNode | null = null
  private stream: MediaStream | null = null

  /**
   * Start microphone capture.
   *
   * Requests getUserMedia, sets up an AudioWorklet node that buffers samples
   * into 100ms PCM chunks, and calls `onChunk` for each chunk.
   *
   * @param onChunk - Callback invoked with each 100ms ArrayBuffer of int16 PCM data
   */
  async start(onChunk: (buffer: ArrayBuffer) => void): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: SAMPLE_RATE,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })

    this.audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })

    // Build the worklet inline via a Blob URL to avoid file-path issues in Electron.
    // The worklet accumulates samples into a BUFFER_SIZE-length buffer, converts
    // them from float32 to int16, and posts the result back to the main thread.
    const workletCode = `
      class AudioChunkProcessor extends AudioWorkletProcessor {
        constructor() {
          super();
          this._buffer = new Float32Array(${BUFFER_SIZE});
          this._pos = 0;
        }

        process(inputs) {
          const input = inputs[0]?.[0];
          if (!input) return true;

          for (let i = 0; i < input.length; i++) {
            this._buffer[this._pos++] = input[i];

            if (this._pos >= ${BUFFER_SIZE}) {
              const int16 = new Int16Array(${BUFFER_SIZE});
              for (let j = 0; j < ${BUFFER_SIZE}; j++) {
                int16[j] = Math.max(-32768, Math.min(32767, Math.round(this._buffer[j] * 32767)));
              }
              // Transfer the buffer ownership to avoid copying
              this.port.postMessage({ buffer: int16.buffer }, [int16.buffer]);
              this._pos = 0;
            }
          }

          return true;
        }
      }

      registerProcessor('audio-chunk-processor', AudioChunkProcessor);
    `

    const blob = new Blob([workletCode], { type: 'application/javascript' })
    const url = URL.createObjectURL(blob)
    await this.audioContext.audioWorklet.addModule(url)
    URL.revokeObjectURL(url)

    const source = this.audioContext.createMediaStreamSource(this.stream)
    this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-chunk-processor')
    this.workletNode.port.onmessage = (e: MessageEvent<{ buffer: ArrayBuffer }>) =>
      onChunk(e.data.buffer)
    source.connect(this.workletNode)
  }

  /**
   * Stop microphone capture and release all resources.
   */
  async stop(): Promise<void> {
    this.workletNode?.disconnect()
    this.workletNode = null

    await this.audioContext?.close()
    this.audioContext = null

    this.stream?.getTracks().forEach((t) => t.stop())
    this.stream = null
  }

  /** Returns true if the AudioContext is currently running. */
  get isActive(): boolean {
    return this.audioContext?.state === 'running'
  }
}
