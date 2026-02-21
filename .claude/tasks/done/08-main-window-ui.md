# Task 08: Main Window UI

## Objective
Build the main application window with session management, full transcript view, settings, and meeting history.

## Steps

### 1. App layout and routing

```tsx
// App.tsx
function App() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/session/:id" element={<SessionView />} />
          <Route path="/live" element={<LiveSession />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
```

### 2. Sidebar component
```
┌──────────────────┐
│  🎙 OpenNode      │
│                    │
│  ▶ New Session     │
│                    │
│  📋 Sessions       │
│  ├─ Meeting 2/21   │
│  ├─ Call 2/20      │
│  └─ Meeting 2/19   │
│                    │
│  ⚙ Settings        │
└──────────────────┘
```

### 3. Dashboard page
- Quick-start recording button (big, prominent)
- Audio source selector (system, mic, both)
- Recent sessions list
- System status (GPU, model loaded, etc.)

### 4. Live session page
- Full-screen transcript view
- Current recording controls (pause/stop)
- Elapsed time
- Audio level indicator (VU meter)
- Language detection indicator

### 5. Session view page
- Full transcript with timestamps
- Speaker labels (color-coded)
- Meeting summary (if generated)
- Action items list
- Export buttons (Markdown, JSON, SRT, TXT)
- Re-generate summary button
- Audio playback (if audio saved)

### 6. Settings page
- **Audio**: Default source, sample rate
- **ASR Model**: Parakeet/Whisper, language preference
- **Overlay**: Position, size, opacity, auto-show
- **Diarization**: Enable/disable, max speakers
- **Summarization**: Provider (Ollama/API), model, auto-summarize
- **Storage**: Data directory, auto-cleanup
- **About**: Version, GPU info, model info

### 7. Zustand store (`electron/src/renderer/store/`)

```typescript
import { create } from 'zustand';

interface AppStore {
  // Recording state
  isRecording: boolean;
  isPaused: boolean;
  elapsedTime: number;

  // Current session
  currentSessionId: string | null;
  transcripts: TranscriptLine[];

  // Sessions list
  sessions: SessionSummary[];

  // Status
  backendStatus: 'starting' | 'ready' | 'error';
  modelLoaded: boolean;
  gpuAvailable: boolean;

  // Actions
  startRecording: (config: CaptureConfig) => void;
  stopRecording: () => void;
  addTranscript: (transcript: TranscriptLine) => void;
  updatePartial: (text: string) => void;
  // ...
}
```

### 8. UI components library
Use Tailwind CSS with a custom theme:
- Dark mode by default (meeting-friendly)
- Accent color: configurable
- Components: Button, Card, Input, Select, Badge, Tooltip

## Acceptance Criteria
- [ ] All pages render correctly
- [ ] Navigation between pages works
- [ ] Live session shows real-time transcripts
- [ ] Session history loads from backend/storage
- [ ] Settings save and persist
- [ ] Responsive layout
- [ ] Dark theme looks professional
- [ ] Keyboard shortcuts for recording controls
