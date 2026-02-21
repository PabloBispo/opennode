import { BrowserWindow, screen } from 'electron'
import path from 'path'

type OverlayPosition = 'top-right' | 'bottom-right' | 'top-left' | 'bottom-left'

const OVERLAY_WIDTH = 380
const OVERLAY_HEIGHT = 220
const OVERLAY_MARGIN = 16

/**
 * WindowManager — responsible for creating, tracking, and managing
 * all BrowserWindow instances (main window and PiP overlay).
 */
export class WindowManager {
  private mainWindow: BrowserWindow | null = null
  private overlayWindow: BrowserWindow | null = null

  /**
   * Create and show the main application window.
   */
  createMainWindow(): BrowserWindow {
    this.mainWindow = new BrowserWindow({
      width: 900,
      height: 700,
      minWidth: 600,
      minHeight: 500,
      titleBarStyle: 'hiddenInset', // macOS native feel
      webPreferences: {
        preload: path.join(__dirname, '../preload/index.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
      },
    })

    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.loadURL('http://localhost:5173')
    } else {
      this.mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
    }

    this.mainWindow.on('closed', () => {
      this.mainWindow = null
    })

    return this.mainWindow
  }

  /**
   * Create and show the PiP overlay window.
   * The overlay is frameless, always-on-top, and transparent.
   */
  createOverlayWindow(): BrowserWindow {
    this.overlayWindow = new BrowserWindow({
      width: OVERLAY_WIDTH,
      height: OVERLAY_HEIGHT,
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      resizable: false,
      skipTaskbar: true,
      show: false, // shown only when toggled
      webPreferences: {
        preload: path.join(__dirname, '../preload/overlay.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
      },
    })

    if (process.env.NODE_ENV === 'development') {
      this.overlayWindow.loadURL('http://localhost:5173/overlay.html')
    } else {
      this.overlayWindow.loadFile(path.join(__dirname, '../renderer/overlay.html'))
    }

    this.overlayWindow.on('closed', () => {
      this.overlayWindow = null
    })

    // Default position: bottom-right
    this.positionOverlay('bottom-right')

    return this.overlayWindow
  }

  /**
   * Toggle the overlay window visibility.
   * Creates the window on first toggle if it does not yet exist.
   */
  toggleOverlay(): void {
    if (!this.overlayWindow || this.overlayWindow.isDestroyed()) {
      this.createOverlayWindow()
      this.overlayWindow?.show()
      return
    }

    if (this.overlayWindow.isVisible()) {
      this.overlayWindow.hide()
    } else {
      this.overlayWindow.show()
    }
  }

  /**
   * Position the overlay window relative to the primary display.
   *
   * @param position - One of the four corner positions.
   */
  positionOverlay(position: OverlayPosition): void {
    if (!this.overlayWindow || this.overlayWindow.isDestroyed()) return

    const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize

    let x: number
    let y: number

    switch (position) {
      case 'top-right':
        x = screenWidth - OVERLAY_WIDTH - OVERLAY_MARGIN
        y = OVERLAY_MARGIN
        break
      case 'top-left':
        x = OVERLAY_MARGIN
        y = OVERLAY_MARGIN
        break
      case 'bottom-left':
        x = OVERLAY_MARGIN
        y = screenHeight - OVERLAY_HEIGHT - OVERLAY_MARGIN
        break
      case 'bottom-right':
      default:
        x = screenWidth - OVERLAY_WIDTH - OVERLAY_MARGIN
        y = screenHeight - OVERLAY_HEIGHT - OVERLAY_MARGIN
        break
    }

    this.overlayWindow.setPosition(x, y)
  }

  /** Returns the main window instance, or null if not created. */
  getMainWindow(): BrowserWindow | null {
    return this.mainWindow
  }

  /** Returns the overlay window instance, or null if not created. */
  getOverlayWindow(): BrowserWindow | null {
    return this.overlayWindow
  }
}
