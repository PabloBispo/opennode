import React, { useEffect, useState } from 'react'
import type { FinalTranscriptMessage } from '@shared/types'

/**
 * Overlay (PiP) root component.
 * Shows the most recent transcript line in a compact, always-on-top window.
 * Full implementation comes in Task 07.
 */
export default function OverlayApp(): React.ReactElement {
  const [lastTranscript, setLastTranscript] = useState<string>('Waiting for transcript…')

  useEffect(() => {
    window.opennode.onFinalTranscript((msg: FinalTranscriptMessage) => {
      setLastTranscript(msg.text)
    })

    return () => {
      window.opennode.removeAllListeners('transcript:final')
    }
  }, [])

  return (
    <div
      className="flex h-screen items-end p-3"
      style={{ background: 'transparent' }}
    >
      <div className="w-full rounded-xl bg-gray-900/80 px-4 py-3 text-sm text-gray-100 shadow-lg backdrop-blur-sm">
        <p className="line-clamp-3 leading-relaxed">{lastTranscript}</p>
      </div>
    </div>
  )
}
