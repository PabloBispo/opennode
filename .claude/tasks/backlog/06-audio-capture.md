# Task 06: System Audio Capture

## Objective
Implement system audio capture (loopback) and microphone capture in Electron, streaming audio to the Python backend.

## Steps

### 1. Install audio capture module
```bash
cd electron
npm install electron-audio-loopback
```

**Platform support:**
- macOS 12.3+ (ScreenCaptureKit)
- Windows 10+ (WASAPI loopback)
- Linux (PulseAudio)

### 2. Audio capture service (`electron/src/main/services/audio-capture.ts`)

```typescript
import { AudioLoopback } from 'electron-audio-loopback';

class AudioCaptureService {
  private loopback: AudioLoopback | null = null;
  private micStream: MediaStream | null = null;
  private wsClient: WebSocket | null = null;
  private isCapturing = false;

  /**
   * Start capturing system audio.
   * Audio format: PCM 16-bit, 16kHz, mono
   */
  async startSystemCapture(): Promise<void> {
    this.loopback = new AudioLoopback({
      sampleRate: 16000,
      channels: 1,
      bitDepth: 16,
    });

    this.loopback.on('data', (buffer: Buffer) => {
      if (this.wsClient?.readyState === WebSocket.OPEN) {
        this.wsClient.send(JSON.stringify({
          type: 'audio_chunk',
          data: buffer.toString('base64'),
          timestamp: Date.now(),
          source: 'system'
        }));
      }
    });

    await this.loopback.start();
    this.isCapturing = true;
  }

  /**
   * Start capturing microphone audio.
   * Uses Web Audio API via renderer process.
   */
  async startMicCapture(): Promise<void> {
    // Request mic via IPC to renderer
    // Renderer uses navigator.mediaDevices.getUserMedia
    // AudioWorklet processes and sends to main via IPC
  }

  /**
   * Mix system + mic audio if both active.
   */
  async startBothCapture(): Promise<void> {
    await this.startSystemCapture();
    await this.startMicCapture();
    // Mix both streams before sending to backend
  }

  async stop(): Promise<void> {
    this.loopback?.stop();
    this.isCapturing = false;
  }
}
```

### 3. Audio processing in renderer (`electron/src/renderer/services/audio-processor.ts`)

For microphone capture via Web Audio API:
```typescript
class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;

  async startMicCapture(): Promise<void> {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      }
    });

    this.audioContext = new AudioContext({ sampleRate: 16000 });
    await this.audioContext.audioWorklet.addModule('/audio-worklet.js');

    const source = this.audioContext.createMediaStreamSource(stream);
    this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-processor');

    this.workletNode.port.onmessage = (event) => {
      // Send PCM data to main process via IPC
      window.opennode.sendAudioChunk(event.data.buffer);
    };

    source.connect(this.workletNode);
  }
}
```

### 4. AudioWorklet processor (`electron/src/renderer/audio-worklet.js`)
```javascript
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 1600; // 100ms at 16kHz
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0][0]; // mono
    if (!input) return true;

    for (let i = 0; i < input.length; i++) {
      this.buffer[this.bufferIndex++] = input[i];
      if (this.bufferIndex >= this.bufferSize) {
        // Convert float32 to int16
        const int16 = new Int16Array(this.bufferSize);
        for (let j = 0; j < this.bufferSize; j++) {
          int16[j] = Math.max(-32768, Math.min(32767, this.buffer[j] * 32768));
        }
        this.port.postMessage({ buffer: int16.buffer }, [int16.buffer]);
        this.bufferIndex = 0;
      }
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
```

### 5. WebSocket client (`electron/src/main/services/ws-client.ts`)
```typescript
import WebSocket from 'ws';

class TranscriptionClient {
  private ws: WebSocket | null = null;

  connect(url: string = 'ws://127.0.0.1:8765/ws/transcribe'): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url);
      this.ws.on('open', resolve);
      this.ws.on('error', reject);
      this.ws.on('message', (data) => this.handleMessage(data));
    });
  }

  sendAudioChunk(buffer: Buffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'audio_chunk',
        data: buffer.toString('base64'),
        timestamp: Date.now()
      }));
    }
  }

  sendControl(action: string, config?: any): void {
    this.ws?.send(JSON.stringify({ type: 'control', action, config }));
  }

  private handleMessage(data: WebSocket.Data): void {
    const msg = JSON.parse(data.toString());
    // Emit to renderer via IPC
  }
}
```

### 6. macOS permissions handling
```typescript
import { systemPreferences } from 'electron';

async function checkPermissions(): Promise<{mic: boolean, screen: boolean}> {
  const mic = systemPreferences.getMediaAccessStatus('microphone') === 'granted';
  const screen = systemPreferences.getMediaAccessStatus('screen') === 'granted';

  if (!mic) {
    await systemPreferences.askForMediaAccess('microphone');
  }
  // Screen recording permission requires user to go to System Preferences

  return { mic, screen };
}
```

## Platform Notes
- **macOS**: Requires "Screen & System Audio Recording" permission. First launch prompts user.
- **Windows**: WASAPI loopback works without special permissions.
- **Linux**: Requires PulseAudio. May need `pavucontrol` for routing.

## Acceptance Criteria
- [ ] System audio capture works on at least one platform
- [ ] Microphone capture works with echo cancellation
- [ ] Audio is correctly formatted as PCM 16-bit 16kHz mono
- [ ] Audio streams to Python backend via WebSocket
- [ ] Permission checks work on macOS
- [ ] Clean start/stop without memory leaks
- [ ] Audio chunks arrive at backend with <100ms latency
