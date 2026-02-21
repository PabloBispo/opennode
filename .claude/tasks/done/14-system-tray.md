# Task 14: System Tray

## Objective
Implement system tray icon with quick controls for recording and overlay.

## Steps

### 1. Tray setup (`electron/src/main/tray.ts`)

```typescript
import { Tray, Menu, nativeImage } from 'electron';

class SystemTray {
  private tray: Tray;

  create() {
    const icon = nativeImage.createFromPath(
      path.join(__dirname, '../../assets/tray-icon.png')
    );

    this.tray = new Tray(icon);
    this.tray.setToolTip('OpenNode');
    this.updateMenu('idle');
  }

  updateMenu(state: 'idle' | 'recording' | 'paused') {
    const menu = Menu.buildFromTemplate([
      {
        label: state === 'recording' ? '⏹ Stop Recording' : '🔴 Start Recording',
        click: () => toggleRecording(),
      },
      {
        label: state === 'recording' ? '⏸ Pause' : undefined,
        visible: state === 'recording',
        click: () => pauseRecording(),
      },
      { type: 'separator' },
      {
        label: 'Show Overlay',
        type: 'checkbox',
        checked: overlayVisible,
        click: () => toggleOverlay(),
      },
      {
        label: 'Open OpenNode',
        click: () => mainWindow?.show(),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => app.quit(),
      },
    ]);

    this.tray.setContextMenu(menu);
  }

  // Update tray icon based on recording state
  setRecordingState(isRecording: boolean) {
    const iconName = isRecording ? 'tray-recording.png' : 'tray-icon.png';
    this.tray.setImage(nativeImage.createFromPath(
      path.join(__dirname, `../../assets/${iconName}`)
    ));
    this.updateMenu(isRecording ? 'recording' : 'idle');
  }
}
```

### 2. Tray icons
Create icons for:
- `tray-icon.png` — Default (microphone icon, 16x16 and 32x32)
- `tray-recording.png` — Recording active (red microphone)
- macOS template images (monochrome for menu bar)

### 3. Quick actions from tray
- Start/stop recording (one click)
- Toggle overlay
- Open main window
- Quit app

### 4. Keep app running when main window closed
```typescript
app.on('window-all-closed', () => {
  // Don't quit — keep in tray
  // On macOS this is standard behavior
  if (process.platform !== 'darwin') {
    // On Windows/Linux, keep running in tray
  }
});
```

## Acceptance Criteria
- [ ] Tray icon appears on all platforms
- [ ] Context menu shows correct options based on state
- [ ] Recording can be started/stopped from tray
- [ ] Overlay toggle works from tray
- [ ] App stays in tray when main window is closed
- [ ] Icon changes when recording
