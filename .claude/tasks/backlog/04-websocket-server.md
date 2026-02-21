# Task 04: WebSocket Server for Real-Time Communication

## Objective
Implement the WebSocket endpoint that receives audio from the Electron frontend, routes it through the processing pipeline, and streams transcription results back.

## Steps

### 1. WebSocket handler (`backend/opennode/server.py`)

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import base64
import numpy as np

@app.websocket("/ws/transcribe")
async def transcribe_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = TranscriptionSession(websocket)

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)

            if data["type"] == "audio_chunk":
                audio_bytes = base64.b64decode(data["data"])
                audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                await session.process_audio(audio, data.get("timestamp"))

            elif data["type"] == "control":
                await session.handle_control(data["action"], data.get("config"))

    except WebSocketDisconnect:
        await session.cleanup()
```

### 2. Transcription session manager (`backend/opennode/pipeline/session.py`)

```python
class TranscriptionSession:
    """Manages a single transcription session."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.vad = SileroVAD()
        self.accumulator = SpeechAccumulator()
        self.asr_engine = get_asr_engine()  # singleton
        self.is_active = False
        self.transcript_chunks = []

    async def process_audio(self, audio: np.ndarray, timestamp: int):
        """Process incoming audio through VAD → ASR pipeline."""
        # 1. Run VAD
        vad_result = self.vad.process_chunk(audio)

        # 2. Accumulate speech
        speech_segment = self.accumulator.add_chunk(vad_result)

        # 3. If we have a complete utterance, transcribe
        if speech_segment is not None:
            result = await self.asr_engine.transcribe(speech_segment)
            await self.send_final_transcript(result)

        # 4. For partial updates during speech, send periodically
        elif vad_result.is_speech and self.accumulator.should_emit_partial():
            partial_audio = self.accumulator.get_current_speech()
            result = await self.asr_engine.transcribe(partial_audio)
            await self.send_partial_transcript(result)

    async def send_partial_transcript(self, result: TranscriptionResult):
        await self.websocket.send_json({
            "type": "partial_transcript",
            "text": result.text,
            "chunk_id": len(self.transcript_chunks),
            "confidence": result.confidence,
            "timestamp_ms": result.start_ms
        })

    async def send_final_transcript(self, result: TranscriptionResult):
        self.transcript_chunks.append(result)
        await self.websocket.send_json({
            "type": "final_transcript",
            "text": result.text,
            "chunk_id": len(self.transcript_chunks) - 1,
            "confidence": result.confidence,
            "start_ms": result.start_ms,
            "end_ms": result.end_ms,
            "words": [w.__dict__ for w in result.words]
        })

    async def handle_control(self, action: str, config: dict = None):
        if action == "start":
            self.is_active = True
            if config:
                # Apply session config (language, model, etc.)
                pass
            await self.send_status("transcribing")
        elif action == "stop":
            self.is_active = False
            await self.finalize_session()
            await self.send_status("stopped")
        elif action == "pause":
            self.is_active = False
            await self.send_status("paused")

    async def finalize_session(self):
        """Save transcript, trigger summarization if enabled."""
        # Save to database
        # Trigger async diarization on full audio
        # Trigger summarization
        pass
```

### 3. Connection manager (multi-client support)
```python
class ConnectionManager:
    """Manages multiple WebSocket connections."""

    def __init__(self):
        self.sessions: dict[str, TranscriptionSession] = {}

    async def connect(self, websocket: WebSocket) -> TranscriptionSession:
        pass

    async def disconnect(self, session_id: str):
        pass
```

### 4. ASR worker thread
Since ASR inference is CPU/GPU bound, run it in a thread pool:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

asr_executor = ThreadPoolExecutor(max_workers=2)

async def run_asr(engine, audio):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(asr_executor, engine.transcribe_sync, audio)
```

### 5. Message validation
Use Pydantic models to validate incoming/outgoing WebSocket messages:
```python
class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"]
    data: str  # base64
    timestamp: int
    session_id: Optional[str]

class ControlMessage(BaseModel):
    type: Literal["control"]
    action: Literal["start", "stop", "pause", "resume"]
    session_id: Optional[str]
    config: Optional[SessionConfig]
```

## Performance Considerations
- Audio chunks arrive every ~50-100ms (depending on frontend buffer size)
- VAD must process in <10ms to not block the pipeline
- ASR runs in thread pool to not block the event loop
- Partial transcripts emitted every 500ms during continuous speech
- Final transcripts emitted at end of each utterance (silence detected)

## Acceptance Criteria
- [ ] WebSocket endpoint accepts connections
- [ ] Audio chunks are received and decoded correctly
- [ ] Control messages (start/stop/pause) work
- [ ] Transcription results are streamed back to client
- [ ] Multiple concurrent sessions are supported
- [ ] ASR runs in thread pool (non-blocking)
- [ ] Graceful handling of disconnections
- [ ] Status messages sent on state changes
