import React, { useEffect, useRef } from 'react'
import { useStore } from '../store'

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${sec.toString().padStart(2, '0')}`
}

const SPEAKER_COLORS: Record<string, string> = {
  SPEAKER_00: '#3B82F6',
  SPEAKER_01: '#10B981',
  SPEAKER_02: '#F59E0B',
  SPEAKER_03: '#EF4444',
  SPEAKER_04: '#8B5CF6',
}

export default function LiveSession() {
  const { transcripts, partialText, elapsedMs, recordingState, setRecordingState, setCurrentView } = useStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts, partialText])

  const handleStop = async () => {
    await window.opennode.stopCapture()
    setRecordingState('idle')
    setCurrentView('dashboard')
  }

  const handlePause = async () => {
    // Toggle pause — will send control:pause to backend via WS
    setRecordingState(recordingState === 'paused' ? 'recording' : 'paused')
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Controls bar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${recordingState === 'recording' ? 'bg-red-500 animate-pulse' : 'bg-yellow-500'}`} />
          <span className="text-sm font-mono text-gray-300">{formatElapsed(elapsedMs)}</span>
        </div>
        <div className="flex-1" />
        <button
          onClick={handlePause}
          className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded text-white"
        >
          {recordingState === 'paused' ? '▶ Resume' : '⏸ Pause'}
        </button>
        <button
          onClick={handleStop}
          className="px-3 py-1.5 text-sm bg-red-700 hover:bg-red-600 rounded text-white"
        >
          ⏹ Stop
        </button>
        <button
          onClick={() => window.opennode.toggleOverlay()}
          className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
        >
          PiP
        </button>
      </div>

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
        {transcripts.length === 0 && !partialText && (
          <div className="text-gray-500 text-sm text-center py-8">Listening...</div>
        )}
        {transcripts.map((t) => (
          <div key={t.id} className="text-sm leading-relaxed">
            {t.speaker && (
              <span
                className="font-semibold mr-2 text-xs"
                style={{ color: SPEAKER_COLORS[t.speaker] ?? '#94A3B8' }}
              >
                {t.speaker.replace('SPEAKER_0', 'S').replace('SPEAKER_', 'S')}:
              </span>
            )}
            <span className="text-white/85">{t.text}</span>
          </div>
        ))}
        {partialText && (
          <div className="text-sm text-white/40 italic">{partialText}▍</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
