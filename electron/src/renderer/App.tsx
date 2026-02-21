import React, { useEffect, useState } from 'react'
import type { StatusMessage } from '@shared/types'

/**
 * Root application component.
 * This is a placeholder implementation — Task 08 will build the full UI.
 */
export default function App(): React.ReactElement {
  const [backendStatus, setBackendStatus] = useState<StatusMessage['state']>('ready')

  useEffect(() => {
    // Listen for backend status updates forwarded from the main process
    window.opennode.onStatus((msg) => {
      setBackendStatus(msg.state)
    })

    return () => {
      window.opennode.removeAllListeners('status')
    }
  }, [])

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Drag region for the custom title bar (macOS hiddenInset) */}
      <div className="h-8 shrink-0" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties} />

      {/* Main content */}
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
    </div>
  )
}
