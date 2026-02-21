# Task 12: Export and Data Storage

## Objective
Implement persistent storage for sessions and export functionality for transcripts.

## Steps

### 1. Database schema (`backend/opennode/storage/models.py`)

Using SQLite with aiosqlite:

```python
# Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_ms INTEGER,
    language TEXT,
    model_used TEXT,
    audio_source TEXT,         -- 'system', 'mic', 'both'
    audio_file_path TEXT,      -- path to saved audio (optional)
    status TEXT DEFAULT 'active'  -- 'active', 'completed', 'error'
);

# Transcripts table
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    text TEXT NOT NULL,
    speaker TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    confidence REAL,
    is_partial BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Summaries table
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id) UNIQUE,
    executive_summary TEXT,
    key_points TEXT,           -- JSON array
    action_items TEXT,         -- JSON array
    decisions TEXT,            -- JSON array
    next_steps TEXT,           -- JSON array
    model_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Speaker profiles table
CREATE TABLE speakers (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    auto_label TEXT,           -- "SPEAKER_00"
    user_label TEXT,           -- "John" (user-assigned)
    color TEXT,
    total_duration_ms INTEGER
);
```

### 2. Database service (`backend/opennode/storage/database.py`)

```python
import aiosqlite

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self):
        """Create tables if they don't exist."""
        pass

    async def create_session(self, **kwargs) -> str:
        pass

    async def add_transcript(self, session_id: str, transcript: TranscriptionResult):
        pass

    async def get_session(self, session_id: str) -> Session:
        pass

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionSummary]:
        pass

    async def save_summary(self, session_id: str, summary: MeetingSummary):
        pass

    async def delete_session(self, session_id: str):
        """Delete session and all related data."""
        pass
```

### 3. Export formats

**Markdown:**
```python
def export_markdown(session: Session) -> str:
    """Export session as formatted Markdown."""
    md = f"# {session.title}\n\n"
    md += f"**Date**: {session.created_at}\n"
    md += f"**Duration**: {format_duration(session.duration_ms)}\n\n"

    if session.summary:
        md += "## Summary\n\n"
        md += session.summary.executive_summary + "\n\n"
        # ... action items, decisions, etc.

    md += "## Transcript\n\n"
    for t in session.transcripts:
        md += f"**[{format_time(t.start_ms)}] {t.speaker}**: {t.text}\n\n"

    return md
```

**SRT (subtitles):**
```python
def export_srt(session: Session) -> str:
    """Export as SRT subtitle format."""
    srt = ""
    for i, t in enumerate(session.transcripts, 1):
        srt += f"{i}\n"
        srt += f"{format_srt_time(t.start_ms)} --> {format_srt_time(t.end_ms)}\n"
        if t.speaker:
            srt += f"[{t.speaker}] "
        srt += f"{t.text}\n\n"
    return srt
```

**JSON:**
```python
def export_json(session: Session) -> dict:
    """Export as structured JSON."""
    return {
        "session": { ... },
        "transcripts": [ ... ],
        "summary": { ... },
        "speakers": [ ... ]
    }
```

**Plain text:**
```python
def export_txt(session: Session) -> str:
    """Export as plain text."""
    pass
```

### 4. Audio file storage (optional)
- Save raw audio to `~/.opennode/audio/{session_id}.wav`
- Configurable: enable/disable audio saving
- Auto-cleanup: delete audio older than X days

### 5. Export API endpoints
```python
@app.get("/api/sessions/{session_id}/export/{format}")
async def export_session(session_id: str, format: str):
    # format: "markdown", "srt", "json", "txt"
    pass
```

### 6. Data directory management
```python
class DataManager:
    def __init__(self, data_dir: str = "~/.opennode"):
        self.data_dir = Path(data_dir).expanduser()
        self.db_path = self.data_dir / "opennode.db"
        self.audio_dir = self.data_dir / "audio"
        self.models_dir = self.data_dir / "models"

    def initialize(self):
        """Create directory structure."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

    def get_storage_usage(self) -> dict:
        """Return disk usage by category."""
        pass

    def cleanup_old_audio(self, max_age_days: int = 30):
        """Delete audio files older than max_age_days."""
        pass
```

## Acceptance Criteria
- [ ] SQLite database initializes correctly
- [ ] Sessions are created, updated, and listed
- [ ] Transcripts are stored and retrieved
- [ ] Summaries are saved per session
- [ ] Markdown export produces clean output
- [ ] SRT export works with video players
- [ ] JSON export includes all data
- [ ] Audio files are optionally saved
- [ ] Storage cleanup works
- [ ] Data directory is configurable
