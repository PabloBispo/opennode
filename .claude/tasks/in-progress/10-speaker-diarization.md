# Task 10: Speaker Diarization

## Objective
Implement speaker identification using pyannote.audio to label who is speaking in the transcript.

## Steps

### 1. Install pyannote
```bash
pip install pyannote.audio
```

**Note**: Requires accepting terms on HuggingFace:
- Go to https://huggingface.co/pyannote/speaker-diarization-3.1
- Accept the license
- Set `HF_TOKEN` environment variable

### 2. Diarization engine (`backend/opennode/diarization/pyannote_engine.py`)

```python
from pyannote.audio import Pipeline
import torch

class DiarizationEngine:
    def __init__(self, hf_token: str, max_speakers: int = 10):
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )
        if torch.cuda.is_available():
            self.pipeline.to(torch.device("cuda"))
        self.max_speakers = max_speakers

    async def diarize(self, audio_path: str) -> list[DiarizationSegment]:
        """
        Run diarization on a complete audio file.
        Returns list of segments with speaker labels.
        """
        diarization = self.pipeline(
            audio_path,
            max_speakers=self.max_speakers
        )

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(DiarizationSegment(
                speaker=speaker,
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000)
            ))
        return segments

    async def diarize_incremental(self, audio_buffer: np.ndarray,
                                   sample_rate: int = 16000) -> list[DiarizationSegment]:
        """
        Run diarization on buffered audio (every 5-10 seconds).
        Used for near-real-time speaker labeling.
        """
        # Save buffer to temp file (pyannote requires file input)
        # Run diarization
        # Return new segments
        pass
```

### 3. Data classes
```python
@dataclass
class DiarizationSegment:
    speaker: str       # "SPEAKER_00", "SPEAKER_01", etc.
    start_ms: int
    end_ms: int

@dataclass
class SpeakerProfile:
    id: str
    label: str         # User-assigned name
    color: str         # For UI display
    total_duration_ms: int
```

### 4. Transcript-diarization alignment

Merge ASR transcripts with diarization results:
```python
def align_transcript_with_speakers(
    transcripts: list[TranscriptionResult],
    diarization: list[DiarizationSegment]
) -> list[AnnotatedTranscript]:
    """
    For each transcript segment, find the corresponding speaker
    based on timestamp overlap.
    """
    annotated = []
    for transcript in transcripts:
        # Find diarization segment with most overlap
        best_speaker = find_best_overlap(transcript, diarization)
        annotated.append(AnnotatedTranscript(
            text=transcript.text,
            speaker=best_speaker,
            start_ms=transcript.start_ms,
            end_ms=transcript.end_ms,
            confidence=transcript.confidence
        ))
    return annotated
```

### 5. Near-real-time strategy

Since full diarization is slow (~2.5% RTF), use a hybrid approach:
1. **During recording**: Run diarization every 10 seconds on the buffered audio
2. **After recording**: Run full diarization on complete audio for best accuracy
3. **Update UI**: Replace near-real-time labels with final labels after session ends

### 6. Speaker name assignment
- Auto-assign colors to speakers (Speaker 1 = blue, Speaker 2 = green, etc.)
- Allow user to rename speakers post-session
- Persist speaker profiles across sessions (voice embeddings for future recognition)

## Performance Notes
- pyannote processes at ~2.5% RTF on GPU (1 hour audio in ~90 seconds)
- Requires ~2GB VRAM in addition to ASR model
- CPU fallback works but is significantly slower
- Consider running diarization only post-session if GPU VRAM is limited

## Acceptance Criteria
- [ ] pyannote loads and runs on test audio
- [ ] Speakers are correctly identified and labeled
- [ ] Transcript-diarization alignment works
- [ ] Incremental diarization runs during recording
- [ ] Full diarization runs after session ends
- [ ] Speaker labels appear in UI (overlay + main window)
- [ ] Users can rename speakers
