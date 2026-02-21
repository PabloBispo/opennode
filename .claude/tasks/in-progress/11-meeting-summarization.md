# Task 11: Meeting Summarization

## Objective
Generate meeting summaries, action items, and key decisions from completed transcripts using local LLMs (Ollama) or external APIs.

## Steps

### 1. Summarizer interface (`backend/opennode/summarization/summarizer.py`)

```python
from abc import ABC, abstractmethod

@dataclass
class MeetingSummary:
    executive_summary: str
    key_points: list[str]
    action_items: list[ActionItem]
    decisions: list[str]
    next_steps: list[str]
    duration_minutes: float
    participants: list[str]

@dataclass
class ActionItem:
    description: str
    assignee: str | None
    deadline: str | None

class Summarizer(ABC):
    @abstractmethod
    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        pass
```

### 2. Ollama provider (local, default)

```python
import httpx

class OllamaSummarizer(Summarizer):
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        prompt = self._build_prompt(transcript, speakers)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=120.0
            )

        return self._parse_response(response.json()["response"])

    def _build_prompt(self, transcript: str, speakers: list[str]) -> str:
        return f"""You are a meeting summarization assistant. Analyze the following meeting transcript and produce a structured summary.

Participants: {', '.join(speakers)}

Transcript:
{transcript}

Produce the following in JSON format:
1. "executive_summary": 3-4 sentence summary of the meeting
2. "key_points": List of important topics discussed
3. "action_items": List of tasks with "description", "assignee" (if mentioned), "deadline" (if mentioned)
4. "decisions": List of decisions made during the meeting
5. "next_steps": List of agreed next steps

Respond ONLY with valid JSON."""
```

### 3. API provider (Claude, OpenAI, Groq)

```python
class APISummarizer(Summarizer):
    """Use external API for summarization."""

    def __init__(self, provider: str, api_key: str, model: str):
        # Support: "anthropic", "openai", "groq"
        pass

    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        # Route to appropriate API
        pass
```

### 4. Summarization trigger

```python
class SummarizationService:
    def __init__(self, config: Settings):
        if config.summarization_provider == "ollama":
            self.summarizer = OllamaSummarizer(config.ollama_model)
        else:
            self.summarizer = APISummarizer(...)

    async def summarize_session(self, session_id: str) -> MeetingSummary:
        """Called when a recording session ends."""
        # 1. Load full transcript from storage
        # 2. Format with speaker labels and timestamps
        # 3. Run summarization
        # 4. Save summary to storage
        # 5. Notify frontend
        pass
```

### 5. Ollama availability check

```python
async def check_ollama() -> dict:
    """Check if Ollama is running and which models are available."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json()["models"]]
            return {"available": True, "models": models}
    except:
        return {"available": False, "models": []}
```

### 6. Transcript formatting for summarization

```python
def format_transcript_for_summary(
    transcripts: list[AnnotatedTranscript],
    max_tokens: int = 100000
) -> str:
    """Format transcript with timestamps and speaker labels."""
    lines = []
    for t in transcripts:
        timestamp = format_timestamp(t.start_ms)
        speaker = t.speaker or "Unknown"
        lines.append(f"[{timestamp}] {speaker}: {t.text}")

    full_text = "\n".join(lines)

    # Truncate if too long for model context
    if len(full_text) > max_tokens * 4:  # rough char-to-token ratio
        # Summarize in chunks
        pass

    return full_text
```

## Acceptance Criteria
- [ ] Ollama summarization works with llama3.2
- [ ] API summarization works with at least one provider
- [ ] Summary includes all required fields
- [ ] Action items extract assignees when mentioned
- [ ] Long transcripts are handled (chunked if needed)
- [ ] Summary is saved to session storage
- [ ] Frontend displays summary in session view
- [ ] Auto-summarize option after recording stops
