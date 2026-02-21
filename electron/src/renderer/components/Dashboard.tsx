import React, { useState } from 'react'
import { useStore } from '../store'
import type { CaptureConfig } from '@shared/types'

export default function Dashboard() {
  const { backendStatus, modelLoaded, gpuAvailable, setRecordingState, setCurrentView, clearTranscripts, sessions } = useStore()
  const [source, setSource] = useState<'system' | 'microphone' | 'both'>('system')
  const [loading, setLoading] = useState(false)

  const handleStart = async () => {
    setLoading(true)
    const config: CaptureConfig = {
      source,
      language: 'auto',
      model: 'parakeet',
      enable_diarization: true,
    }
    try {
      await window.opennode.startCapture(config)
      clearTranscripts()
      setRecordingState('recording')
      setCurrentView('live')
    } finally {
      setLoading(false)
    }
  }

  const isReady = backendStatus === 'ready'

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white p-8">
      {/* Status bar */}
      <div className="flex items-center gap-3 mb-8 text-sm">
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs ${isReady ? 'bg-green-900/40 text-green-400 border border-green-800' : 'bg-gray-800 text-gray-400 border border-gray-700'}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${isReady ? 'bg-green-400' : 'bg-gray-500'}`} />
          {backendStatus === 'starting' ? 'Starting backend...' : backendStatus === 'ready' ? 'Ready' : 'Backend offline'}
        </div>
        {gpuAvailable && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-purple-900/40 text-purple-400 border border-purple-800">
            <span>GPU</span>
          </div>
        )}
        {modelLoaded && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-blue-900/40 text-blue-400 border border-blue-800">
            <span>Model loaded</span>
          </div>
        )}
      </div>

      {/* Main CTA */}
      <div className="flex-1 flex flex-col items-center justify-center max-w-md mx-auto w-full">
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-bold text-white mb-2">OpenNode</h1>
          <p className="text-gray-400">Local-first meeting transcription</p>
        </div>

        {/* Source selector */}
        <div className="flex gap-2 mb-6 w-full">
          {(['system', 'microphone', 'both'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={`flex-1 py-2 px-3 rounded text-sm capitalize transition-colors ${
                source === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {s === 'system' ? '🖥 System' : s === 'microphone' ? '🎤 Mic' : '🔀 Both'}
            </button>
          ))}
        </div>

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={!isReady || loading}
          className={`w-full py-4 rounded-xl text-lg font-semibold transition-all ${
            isReady && !loading
              ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg hover:shadow-red-900/30'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          {loading ? 'Starting...' : !isReady ? 'Waiting for backend...' : '⏺ Start Recording'}
        </button>
      </div>

      {/* Recent sessions */}
      {sessions.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">Recent Sessions</h2>
          <div className="space-y-2">
            {sessions.slice(0, 3).map(s => (
              <div key={s.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <div className="text-sm text-white">{s.title || 'Untitled'}</div>
                  <div className="text-xs text-gray-500">{new Date(s.created_at).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
