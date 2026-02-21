import React, { useState, useEffect, useRef, useCallback } from 'react'
import type { OverlayAPI } from './env.d'

// Cast window.opennode to the overlay-specific API type
const overlayAPI = window.opennode as unknown as OverlayAPI

interface TranscriptLine {
  id: number
  text: string
  speaker?: string
  isPartial: boolean
  timestamp: number
}

const SPEAKER_COLORS: Record<string, string> = {
  'SPEAKER_00': '#3B82F6',
  'SPEAKER_01': '#10B981',
  'SPEAKER_02': '#F59E0B',
  'SPEAKER_03': '#EF4444',
  'SPEAKER_04': '#8B5CF6',
}

function getSpeakerColor(speaker: string): string {
  return SPEAKER_COLORS[speaker] ?? '#94A3B8'
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function OverlayApp() {
  const [transcripts, setTranscripts] = useState<TranscriptLine[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const scrollRef = useRef<HTMLDivElement>(null)
  const idCounter = useRef(0)
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current && !isMinimized) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcripts, isMinimized])

  // Listen to transcript events
  useEffect(() => {
    overlayAPI.onPartialTranscript((data) => {
      setIsRecording(true)
      setTranscripts(prev => {
        const withoutPartial = prev.filter(t => !t.isPartial)
        return [
          ...withoutPartial,
          {
            id: idCounter.current++,
            text: data.text,
            isPartial: true,
            timestamp: data.timestamp_ms,
          },
        ]
      })
    })

    overlayAPI.onFinalTranscript((data) => {
      setIsRecording(true)
      setTranscripts(prev => {
        const withoutPartial = prev.filter(t => !t.isPartial)
        return [
          ...withoutPartial,
          {
            id: idCounter.current++,
            text: data.text,
            speaker: data.speaker,
            isPartial: false,
            timestamp: data.start_ms,
          },
        ]
      })
    })

    overlayAPI.onStatus((data) => {
      setIsRecording(data.state === 'transcribing')
    })

    return () => {
      overlayAPI.removeAllListeners('transcript:partial')
      overlayAPI.removeAllListeners('transcript:final')
      overlayAPI.removeAllListeners('status')
    }
  }, [])

  // Elapsed timer
  useEffect(() => {
    if (isRecording) {
      elapsedTimer.current = setInterval(() => setElapsed(e => e + 1), 1000)
    } else {
      if (elapsedTimer.current) clearInterval(elapsedTimer.current)
    }
    return () => { if (elapsedTimer.current) clearInterval(elapsedTimer.current) }
  }, [isRecording])

  // Drag handlers for header
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true)
    setDragStart({ x: e.screenX, y: e.screenY })
    overlayAPI.setClickThrough(false)
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return
    const deltaX = e.screenX - dragStart.x
    const deltaY = e.screenY - dragStart.y
    if (Math.abs(deltaX) > 1 || Math.abs(deltaY) > 1) {
      overlayAPI.drag(deltaX, deltaY)
      setDragStart({ x: e.screenX, y: e.screenY })
    }
  }, [isDragging, dragStart])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  // Click-through when mouse leaves
  const handleMouseLeave = useCallback(() => {
    if (!isDragging) overlayAPI.setClickThrough(true)
  }, [isDragging])

  const handleMouseEnter = useCallback(() => {
    overlayAPI.setClickThrough(false)
  }, [])

  // Keep last 10 transcript lines
  const visibleTranscripts = transcripts.slice(-10)

  if (isMinimized) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-full cursor-default select-none"
        style={{
          background: 'rgba(20, 20, 20, 0.90)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.1)',
          WebkitAppRegion: 'drag',
        } as React.CSSProperties}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {isRecording && (
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
        )}
        <span className="text-xs text-white/70 font-mono">
          {isRecording ? formatElapsed(elapsed) : 'OpenNode'}
        </span>
        <button
          onClick={() => setIsMinimized(false)}
          className="text-white/50 hover:text-white text-xs ml-1"
          style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
        >
          ▲
        </button>
      </div>
    )
  }

  return (
    <div
      className="flex flex-col rounded-xl overflow-hidden select-none"
      style={{
        background: 'rgba(15, 15, 20, 0.88)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        width: '100vw',
        height: '100vh',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 flex-shrink-0 cursor-move"
        style={{
          background: 'rgba(255,255,255,0.04)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          WebkitAppRegion: 'no-drag',
        } as React.CSSProperties}
        onMouseDown={handleMouseDown}
      >
        {isRecording ? (
          <div className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0"
            style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />
        ) : (
          <div className="w-2 h-2 rounded-full bg-gray-600 flex-shrink-0" />
        )}
        <span className="text-xs text-white/60 flex-1">
          {isRecording ? `Recording ${formatElapsed(elapsed)}` : 'OpenNode'}
        </span>
        <button
          onClick={() => setIsMinimized(true)}
          className="text-white/30 hover:text-white/70 text-xs px-1"
          title="Minimize"
        >
          ─
        </button>
        <button
          onClick={() => overlayAPI.close()}
          className="text-white/30 hover:text-red-400 text-xs px-1"
          title="Hide"
        >
          ×
        </button>
      </div>

      {/* Transcript area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-1"
        style={{ scrollbarWidth: 'none' }}
      >
        {visibleTranscripts.length === 0 ? (
          <div className="text-white/25 text-xs text-center py-4">
            {isRecording ? 'Listening...' : 'Waiting for recording...'}
          </div>
        ) : (
          visibleTranscripts.map((line) => (
            <div key={line.id} className={`text-xs leading-relaxed ${line.isPartial ? 'text-white/50' : 'text-white/85'}`}>
              {line.speaker && (
                <span
                  className="font-semibold mr-1 text-[10px]"
                  style={{ color: getSpeakerColor(line.speaker) }}
                >
                  {line.speaker.replace('SPEAKER_0', 'S').replace('SPEAKER_', 'S')}:
                </span>
              )}
              {line.text}
              {line.isPartial && <span className="text-white/30 ml-1">▍</span>}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
