# Task 07: Floating Overlay Window (Picture-in-Picture)

## Objective
Create a transparent, always-on-top overlay window that shows live transcription — similar to Notion's meeting notes widget.

## Steps

### 1. Create overlay BrowserWindow (`electron/src/main/windows/overlay.ts`)

```typescript
import { BrowserWindow, screen } from 'electron';

function createOverlayWindow(): BrowserWindow {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  const overlay = new BrowserWindow({
    width: 420,
    height: 200,
    x: width - 440,  // bottom-right
    y: height - 220,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,  // transparent + resizable is buggy
    hasShadow: false,
    focusable: false,   // don't steal focus from meetings
    webPreferences: {
      preload: path.join(__dirname, '../../preload/overlay.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Allow click-through on non-interactive areas
  overlay.setIgnoreMouseEvents(true, { forward: true });

  if (process.env.NODE_ENV === 'development') {
    overlay.loadURL('http://localhost:5173/overlay.html');
  } else {
    overlay.loadFile(path.join(__dirname, '../../renderer/overlay.html'));
  }

  return overlay;
}
```

### 2. Overlay React UI (`electron/src/overlay/`)

```tsx
// OverlayApp.tsx
function OverlayApp() {
  const [transcripts, setTranscripts] = useState<TranscriptLine[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    window.opennode.onPartialTranscript((data) => {
      // Update last line if partial
      setTranscripts(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { ...updated[updated.length - 1], text: data.text, isPartial: true };
        return updated;
      });
    });

    window.opennode.onFinalTranscript((data) => {
      setTranscripts(prev => [
        ...prev.filter(t => !t.isPartial),
        { text: data.text, speaker: data.speaker, timestamp: data.startMs, isPartial: false }
      ]);
    });
  }, []);

  return (
    <div className="overlay-container">
      <div className="overlay-header">
        <div className="recording-indicator" />
        <span>OpenNode</span>
        <div className="drag-handle" />
      </div>
      <div className="transcript-scroll" ref={scrollRef}>
        {transcripts.map((t, i) => (
          <TranscriptLine key={i} {...t} />
        ))}
      </div>
    </div>
  );
}
```

### 3. Overlay CSS
```css
/* Semi-transparent dark background with blur */
.overlay-container {
  background: rgba(20, 20, 20, 0.85);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  font-family: -apple-system, system-ui, sans-serif;
  color: white;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.overlay-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 8px;
  -webkit-app-region: drag; /* Make header draggable */
}

.recording-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  animation: pulse 1.5s ease-in-out infinite;
}

.transcript-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  font-size: 13px;
  line-height: 1.5;
}

/* Auto-scroll to bottom */
.transcript-scroll {
  scroll-behavior: smooth;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

### 4. Drag-to-reposition
```typescript
// In main process: handle drag via IPC
ipcMain.on('overlay:drag', (_, { deltaX, deltaY }) => {
  if (overlayWindow) {
    const [x, y] = overlayWindow.getPosition();
    overlayWindow.setPosition(x + deltaX, y + deltaY);
  }
});
```

### 5. Click-through behavior
The overlay should be mostly transparent to clicks (so you can interact with the meeting behind it), except for:
- The header bar (draggable)
- The minimize/close buttons
- Scroll area (optional: only when hovered)

```typescript
// Toggle click-through based on mouse position
overlay.setIgnoreMouseEvents(true, { forward: true });

// In renderer, detect mouse enter/leave on interactive areas
document.addEventListener('mouseenter', () => {
  window.opennode.setClickThrough(false);
});
document.addEventListener('mouseleave', () => {
  window.opennode.setClickThrough(true);
});
```

### 6. Overlay controls
- **Minimize**: Collapse to a small pill (just recording indicator)
- **Expand**: Show full transcript view
- **Close**: Hide overlay (accessible from tray)
- **Position presets**: top-right, bottom-right, bottom-left

### 7. Overlay preload (`electron/src/preload/overlay.ts`)
Expose only necessary APIs to overlay window (minimal surface).

## Visual Design

```
┌──────────────────────────────────┐
│ 🔴 OpenNode          ─  ×       │  ← Draggable header
├──────────────────────────────────┤
│ Speaker 1: Hello, can everyone   │
│ hear me?                         │
│                                  │
│ Speaker 2: Yes, I can hear you   │
│ perfectly.                       │
│                                  │
│ Speaker 1: Great, let's start    │
│ with the quarterly review...     │  ← Live text, auto-scrolling
│                                  │
│ ▍typing...                       │  ← Partial transcript indicator
└──────────────────────────────────┘
```

Minimized state:
```
┌───────────────────┐
│ 🔴 Recording 2:34 │
└───────────────────┘
```

## Acceptance Criteria
- [ ] Overlay window appears above other apps
- [ ] Semi-transparent with blur effect
- [ ] Draggable by header
- [ ] Click-through on non-interactive areas
- [ ] Live transcript updates (partial + final)
- [ ] Auto-scrolls to latest text
- [ ] Minimize/expand toggle
- [ ] Recording indicator with elapsed time
- [ ] Speaker labels displayed
- [ ] Smooth animations
