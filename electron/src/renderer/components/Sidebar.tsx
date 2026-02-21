import React from 'react'
import { useStore } from '../store'

export default function Sidebar() {
  const { currentView, setCurrentView, sessions, selectedSessionId, setSelectedSession, recordingState } = useStore()

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col">
      {/* App title */}
      <div className="px-4 py-4 border-b border-gray-800" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${recordingState === 'recording' ? 'bg-red-500 animate-pulse' : 'bg-gray-600'}`} />
          <span className="text-sm font-semibold text-white">OpenNode</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        <button
          onClick={() => setCurrentView('dashboard')}
          className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 ${currentView === 'dashboard' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-900'}`}
        >
          <span>🏠</span> Dashboard
        </button>

        {recordingState !== 'idle' && (
          <button
            onClick={() => setCurrentView('live')}
            className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 ${currentView === 'live' ? 'bg-gray-800 text-white' : 'text-red-400 hover:text-white hover:bg-gray-900'}`}
          >
            <span className="animate-pulse">🔴</span> Live
          </button>
        )}

        {sessions.length > 0 && (
          <div className="mt-3">
            <div className="px-4 py-1 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Sessions</div>
            {sessions.slice(0, 20).map((s) => (
              <button
                key={s.id}
                onClick={() => { setSelectedSession(s.id); setCurrentView('session') }}
                className={`w-full text-left px-4 py-2 text-xs truncate ${selectedSessionId === s.id && currentView === 'session' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-900'}`}
              >
                {s.title || new Date(s.created_at).toLocaleDateString()}
              </button>
            ))}
          </div>
        )}
      </nav>

      {/* Settings button */}
      <div className="p-3 border-t border-gray-800">
        <button
          onClick={() => setCurrentView('settings')}
          className={`w-full text-left px-3 py-2 text-sm rounded flex items-center gap-2 ${currentView === 'settings' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-900'}`}
        >
          ⚙ Settings
        </button>
      </div>
    </aside>
  )
}
