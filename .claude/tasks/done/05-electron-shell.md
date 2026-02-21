# Task 05: Electron Application Shell

## Objective
Create the Electron application with main process, renderer, and the basic window management.

## Steps

### 1. Main process (`electron/src/main/index.ts`)

```typescript
import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';

let mainWindow: BrowserWindow | null = null;
let overlayWindow: BrowserWindow | null = null;

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 500,
    titleBarStyle: 'hiddenInset', // macOS native feel
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }
}

app.whenReady().then(() => {
  createMainWindow();
  // Setup IPC handlers
  // Setup system tray (Task 14)
  // Start Python backend (Task 09)
});
```

### 2. Preload script (`electron/src/preload/index.ts`)

Expose safe APIs to renderer:
```typescript
import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('opennode', {
  // Audio
  startCapture: (config: CaptureConfig) => ipcRenderer.invoke('audio:start', config),
  stopCapture: () => ipcRenderer.invoke('audio:stop'),

  // Transcription
  onPartialTranscript: (cb: (data: PartialTranscript) => void) =>
    ipcRenderer.on('transcript:partial', (_, data) => cb(data)),
  onFinalTranscript: (cb: (data: FinalTranscript) => void) =>
    ipcRenderer.on('transcript:final', (_, data) => cb(data)),
  onStatus: (cb: (data: Status) => void) =>
    ipcRenderer.on('status', (_, data) => cb(data)),

  // Sessions
  getSessions: () => ipcRenderer.invoke('sessions:list'),
  getSession: (id: string) => ipcRenderer.invoke('sessions:get', id),
  deleteSession: (id: string) => ipcRenderer.invoke('sessions:delete', id),

  // Settings
  getSettings: () => ipcRenderer.invoke('settings:get'),
  updateSettings: (settings: Partial<Settings>) => ipcRenderer.invoke('settings:update', settings),

  // Overlay
  toggleOverlay: () => ipcRenderer.invoke('overlay:toggle'),

  // App
  getSystemInfo: () => ipcRenderer.invoke('app:system-info'),
});
```

### 3. Renderer entry point (`electron/src/renderer/`)

React app with:
- `App.tsx` — Root component with router
- `main.tsx` — React DOM entry point
- `index.html` — HTML shell

### 4. Vite + Electron configuration

Use `electron-vite` or `vite-plugin-electron`:
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import electron from 'vite-plugin-electron';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react(),
    electron([
      { entry: 'src/main/index.ts' },
      { entry: 'src/preload/index.ts' },
    ]),
  ],
});
```

### 5. TypeScript types (`electron/src/shared/types.ts`)

Define shared types between main/renderer/preload:
```typescript
interface CaptureConfig {
  source: 'system' | 'microphone' | 'both';
  language: string;
  model: 'parakeet' | 'whisper';
  enableDiarization: boolean;
}

interface PartialTranscript {
  text: string;
  chunkId: number;
  confidence: number;
  timestampMs: number;
}

interface FinalTranscript {
  text: string;
  chunkId: number;
  confidence: number;
  speaker?: string;
  startMs: number;
  endMs: number;
  words: WordTimestamp[];
}

// ... etc
```

### 6. Window management service
Handle creating/destroying/positioning windows:
```typescript
class WindowManager {
  createMainWindow(): BrowserWindow;
  createOverlayWindow(): BrowserWindow;
  toggleOverlay(): void;
  positionOverlay(position: 'top-right' | 'bottom-right' | 'custom'): void;
}
```

## Acceptance Criteria
- [ ] Electron app starts and shows main window
- [ ] Vite HMR works in development mode
- [ ] Preload script exposes APIs correctly
- [ ] IPC communication works between main ↔ renderer
- [ ] TypeScript compiles without errors
- [ ] Window management handles show/hide/position
