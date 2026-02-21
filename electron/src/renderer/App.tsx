import React, { useEffect, useRef, useState } from 'react'
import type { StatusMessage } from '@shared/types'
import Settings from './components/Settings'
import { MicAudioProcessor } from './services/audio-processor'

/**
 * Root application component.
 * Renders either the main transcription view or the Settings panel depending
 * on whether the user has clicked the settings gear icon.
 *
 * Audio flow:
 * 1. The main process sends `audio:start-mic` when recording starts.
 * 2. The renderer creates a `MicAudioProcessor` and starts capturing mic audio.
 * 3. Each PCM chunk is sent back to the main process via `window.opennode.sendAudioChunk`.
 * 4. The main process forwards the chunk to the Python backend over WebSocket.
 * 5. On `audio:stop-mic`, the processor is stopped and resources are released.
 */
export default function App(): React.ReactElement {
  const [backendStatus, setBackendStatus] = useState<StatusMessage['state']>('ready')
  const [showSettings, setShowSettings] = useState(false)
  const micProcessorRef = useRef<MicAudioProcessor | null>(null)

  useEffect(() => {
    // Listen for backend status updates forwarded from the main process
    window.opennode.onStatus((msg) => {
      setBackendStatus(msg.state)
    })

    // Main process instructs renderer to start microphone capture
    window.opennode.onStartMic((_config) => {
      const processor = new MicAudioProcessor()
      micProcessorRef.current = processor

      processor
        .start((buffer) => {
          window.opennode.sendAudioChunk(buffer)
        })
        .catch((err) => {
          console.error('[App] Failed to start mic capture:', err)
        })
    })

    // Main process instructs renderer to stop microphone capture
    window.opennode.onStopMic(() => {
      micProcessorRef.current
        ?.stop()
        .catch((err) => console.error('[App] Failed to stop mic capture:', err))
      micProcessorRef.current = null
    })

    return () => {
      window.opennode.removeAllListeners('status')
      window.opennode.removeAllListeners('audio:start-mic')
      window.opennode.removeAllListeners('audio:stop-mic')

      // Stop mic processor if active when component unmounts
      micProcessorRef.current
        ?.stop()
        .catch((err) => console.error('[App] Failed to stop mic capture on unmount:', err))
      micProcessorRef.current = null
    }
  }, [])

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Title bar — draggable on macOS, houses settings toggle */}
      <div
        className="h-10 shrink-0 flex items-center justify-between px-4"
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      >
        <span className="text-xs font-semibold text-gray-500 select-none">OpenNode</span>

        {/* Settings button — must opt out of the drag region */}
        <button
          onClick={() => setShowSettings((v) => !v)}
          title={showSettings ? 'Back to app' : 'Settings'}
          style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
          className="p-1.5 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        >
          {showSettings ? (
            /* X icon when settings are open */
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            /* Gear icon when settings are hidden */
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          )}
        </button>
      </div>

      {/* Content area — either Settings panel or main app view */}
      {showSettings ? (
        <div className="flex-1 overflow-hidden">
          <Settings />
        </div>
      ) : (
        <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
          <h1 className="text-4xl font-bold tracking-tight text-white">OpenNode</h1>
          <p className="text-lg text-gray-400">
            Real-time meeting transcription &amp; summarization
          </p>

          <div className="flex items-center gap-2 rounded-full bg-gray-800 px-4 py-2 text-sm">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === 'transcribing'
                  ? 'bg-green-400'
                  : backendStatus === 'error'
                    ? 'bg-red-400'
                    : backendStatus === 'paused'
                      ? 'bg-yellow-400'
                      : 'bg-gray-500'
              }`}
            />
            <span className="capitalize text-gray-300">{backendStatus}</span>
          </div>

          <p className="text-center text-xs text-gray-600">
            Full UI coming in Task 08 · Overlay in Task 07
          </p>
        </main>
      )}
    </div>
  )
}
