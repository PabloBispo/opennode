# Task 13: Settings and Configuration

## Objective
Implement a comprehensive settings system that persists user preferences across sessions.

## Steps

### 1. Electron-side settings (`electron/src/main/services/settings.ts`)

Use `electron-store` for persistent settings:
```typescript
import Store from 'electron-store';

interface AppSettings {
  // Audio
  audioSource: 'system' | 'microphone' | 'both';

  // ASR
  asrEngine: 'parakeet' | 'whisper';
  language: string;  // 'auto' or ISO code

  // Overlay
  overlayEnabled: boolean;
  overlayPosition: { x: number; y: number };
  overlaySize: { width: number; height: number };
  overlayOpacity: number;
  overlayAutoShow: boolean;  // auto-show when recording starts

  // Diarization
  enableDiarization: boolean;
  maxSpeakers: number;

  // Summarization
  enableSummarization: boolean;
  summarizationProvider: 'ollama' | 'anthropic' | 'openai' | 'groq';
  summarizationModel: string;
  summarizationApiKey: string;
  autoSummarize: boolean;  // auto-summarize when recording stops

  // Storage
  dataDirectory: string;
  saveAudio: boolean;
  audioRetentionDays: number;

  // UI
  theme: 'dark' | 'light' | 'system';
  fontSize: number;

  // Keyboard shortcuts
  shortcuts: {
    toggleRecording: string;
    toggleOverlay: string;
    togglePause: string;
  };

  // Backend
  backendPort: number;
}

const store = new Store<AppSettings>({
  defaults: {
    audioSource: 'system',
    asrEngine: 'parakeet',
    language: 'auto',
    overlayEnabled: true,
    overlayPosition: { x: -1, y: -1 },  // auto
    overlaySize: { width: 420, height: 200 },
    overlayOpacity: 0.85,
    overlayAutoShow: true,
    enableDiarization: true,
    maxSpeakers: 10,
    enableSummarization: true,
    summarizationProvider: 'ollama',
    summarizationModel: 'llama3.2',
    summarizationApiKey: '',
    autoSummarize: true,
    dataDirectory: '~/.opennode',
    saveAudio: false,
    audioRetentionDays: 30,
    theme: 'dark',
    fontSize: 14,
    shortcuts: {
      toggleRecording: 'CommandOrControl+Shift+R',
      toggleOverlay: 'CommandOrControl+Shift+O',
      togglePause: 'CommandOrControl+Shift+P',
    },
    backendPort: 8765,
  }
});
```

### 2. Settings sync to backend
When settings change, push relevant config to Python backend:
```typescript
async function syncSettingsToBackend(settings: Partial<AppSettings>) {
  // Update backend config via HTTP endpoint
  await fetch(`http://127.0.0.1:${port}/api/config`, {
    method: 'PATCH',
    body: JSON.stringify(settings)
  });
}
```

### 3. Global keyboard shortcuts
```typescript
import { globalShortcut } from 'electron';

function registerShortcuts(settings: AppSettings) {
  globalShortcut.register(settings.shortcuts.toggleRecording, () => {
    // Toggle recording
  });
  globalShortcut.register(settings.shortcuts.toggleOverlay, () => {
    // Toggle overlay visibility
  });
}
```

### 4. Settings UI (React component)
Organized in tabs/sections:
- General (language, theme)
- Audio (source, format)
- Models (ASR engine, summarization)
- Overlay (position, size, auto-show)
- Storage (data dir, cleanup)
- Shortcuts (keyboard bindings)
- About (version, system info)

### 5. Settings validation
Validate settings before saving:
- Port numbers in valid range
- API keys non-empty when provider selected
- Paths exist and are writable
- Shortcuts don't conflict

## Acceptance Criteria
- [ ] Settings persist across app restarts
- [ ] All settings are configurable from UI
- [ ] Settings changes propagate to backend
- [ ] Global keyboard shortcuts work
- [ ] Default values are sensible
- [ ] Settings validation prevents invalid configs
