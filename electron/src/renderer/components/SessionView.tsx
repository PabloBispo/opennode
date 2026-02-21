import React, { useEffect, useState } from 'react'
import { useStore } from '../store'

const BACKEND_URL = 'http://127.0.0.1:8765'

export default function SessionView() {
  const { selectedSessionId } = useStore()
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!selectedSessionId) return
    setLoading(true)
    // Fetch full session via backend REST
    fetch(`${BACKEND_URL}/api/sessions/${selectedSessionId}`)
      .then(r => r.json())
      .then(data => { setSession(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [selectedSessionId])

  if (!selectedSessionId) return <div className="p-8 text-gray-500">Select a session</div>
  if (loading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!session) return <div className="p-8 text-red-400">Session not found</div>

  const exportSession = async (format: string) => {
    const res = await fetch(`${BACKEND_URL}/api/sessions/${selectedSessionId}/export/${format}`)
    const text = await res.text()
    const blob = new Blob([text], { type: format === 'json' ? 'application/json' : 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `session-${selectedSessionId}.${format === 'markdown' ? 'md' : format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const transcripts = session.transcripts ?? []
  const summary = session.summary

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800 flex-shrink-0">
        <div className="flex-1">
          <h2 className="text-lg font-semibold">{session.session?.title || 'Session'}</h2>
          <div className="text-xs text-gray-500">
            {session.session?.created_at ? new Date(session.session.created_at).toLocaleString() : ''}
          </div>
        </div>
        <div className="flex gap-2">
          {['markdown', 'srt', 'json', 'txt'].map(fmt => (
            <button
              key={fmt}
              onClick={() => exportSession(fmt)}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Summary */}
        {summary && (
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-2">Summary</h3>
            <p className="text-sm text-white/80 mb-3">{summary.executive_summary}</p>
            {summary.action_items?.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-500 mb-1">Action Items</div>
                <ul className="space-y-1">
                  {summary.action_items.map((item: string, i: number) => (
                    <li key={i} className="text-xs text-white/70 flex gap-2">
                      <span className="text-blue-400">•</span> {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Transcript */}
        <div className="px-6 py-4 space-y-2">
          {transcripts.map((t: any, i: number) => (
            <div key={i} className="text-sm leading-relaxed">
              <span className="text-gray-600 text-xs font-mono mr-2">
                {Math.floor(t.start_ms / 60000)}:{String(Math.floor((t.start_ms % 60000) / 1000)).padStart(2, '0')}
              </span>
              {t.speaker && <span className="text-blue-400 text-xs mr-2">{t.speaker}:</span>}
              <span className="text-white/85">{t.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
