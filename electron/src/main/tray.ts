import { Tray, Menu, nativeImage, app } from 'electron'

type TrayState = 'idle' | 'recording' | 'paused'

/**
 * Creates a simple monochrome icon from raw pixel data.
 * This avoids needing external PNG files during development.
 */
function createTrayIcon(recording: boolean): Electron.NativeImage {
  // Use a 16x16 RGBA buffer — a simple circle
  const size = 16
  const buffer = Buffer.alloc(size * size * 4)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = x - size / 2
      const dy = y - size / 2
      const dist = Math.sqrt(dx * dx + dy * dy)
      const idx = (y * size + x) * 4
      const inside = dist <= size / 2 - 1
      buffer[idx] = recording ? 220 : 150     // R
      buffer[idx + 1] = recording ? 50 : 150  // G
      buffer[idx + 2] = recording ? 50 : 150  // B
      buffer[idx + 3] = inside ? 255 : 0      // A
    }
  }
  return nativeImage.createFromBuffer(buffer, { width: size, height: size })
}

export class SystemTray {
  private tray: Tray | null = null
  private _state: TrayState = 'idle'
  private _overlayVisible = false
  private _onToggleRecording: (() => void) | null = null
  private _onToggleOverlay: (() => void) | null = null
  private _onShowMainWindow: (() => void) | null = null

  create(options: {
    onToggleRecording: () => void
    onToggleOverlay: () => void
    onShowMainWindow: () => void
  }): void {
    this._onToggleRecording = options.onToggleRecording
    this._onToggleOverlay = options.onToggleOverlay
    this._onShowMainWindow = options.onShowMainWindow

    const icon = createTrayIcon(false)
    this.tray = new Tray(icon)
    this.tray.setToolTip('OpenNode')
    this._updateMenu()

    // Double-click on tray icon shows main window
    this.tray.on('double-click', () => this._onShowMainWindow?.())
  }

  setState(state: TrayState): void {
    this._state = state
    this._updateIconForState()
    this._updateMenu()
  }

  setOverlayVisible(visible: boolean): void {
    this._overlayVisible = visible
    this._updateMenu()
  }

  destroy(): void {
    this.tray?.destroy()
    this.tray = null
  }

  private _updateIconForState(): void {
    if (!this.tray) return
    const isRecording = this._state === 'recording'
    this.tray.setImage(createTrayIcon(isRecording))
    this.tray.setToolTip(
      this._state === 'recording' ? 'OpenNode — Recording'
      : this._state === 'paused' ? 'OpenNode — Paused'
      : 'OpenNode'
    )
  }

  private _updateMenu(): void {
    if (!this.tray) return

    const isRecording = this._state !== 'idle'

    const template: Electron.MenuItemConstructorOptions[] = [
      {
        label: isRecording
          ? (this._state === 'paused' ? '▶ Resume Recording' : '⏹ Stop Recording')
          : '⏺ Start Recording',
        click: () => this._onToggleRecording?.(),
      },
    ]

    if (this._state === 'recording') {
      template.push({
        label: '⏸ Pause',
        click: () => this._onToggleRecording?.(), // simplified — real pause would need separate action
      })
    }

    template.push(
      { type: 'separator' },
      {
        label: this._overlayVisible ? '✓ Show Overlay' : 'Show Overlay',
        type: 'checkbox',
        checked: this._overlayVisible,
        click: () => this._onToggleOverlay?.(),
      },
      {
        label: 'Open OpenNode',
        click: () => this._onShowMainWindow?.(),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => app.quit(),
      },
    )

    this.tray.setContextMenu(Menu.buildFromTemplate(template))
  }
}

export const systemTray = new SystemTray()
