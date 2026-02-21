import React, { useEffect, useRef } from 'react'
import { useStore } from './store'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import LiveSession from './components/LiveSession'
import SessionView from './components/SessionView'
import Settings from './components/Settings'
import { MicAudioProcessor } from './services/audio-processor'

/**
 * Root application component.
 *
 * Responsibilities:
 * - Wire up all window.opennode IPC event listeners
 * - Manage the elapsed recording timer
 * - Load sessions on mount / when backend is ready
 * - Handle microphone audio processor lifecycle
 * - Render the sidebar + current view (Dashboard, LiveSession, SessionView, Settings)
 */
export default function App(): React.ReactElement {
  const {
    currentView,
    addTranscript,
    setPartialText,
    setBackendStatus,
    setModelLoaded,
    setGpuAvailable,
    setSessions,
    recordingState,
    tickElapsed,
    resetElapsed,
  } = useStore()

  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const micProcessorRef = useRef<MicAudioProcessor | null>(null)

  // Start/stop elapsed timer based on recording state
  useEffect(() => {
    if (recordingState === 'recording') {
      elapsedTimer.current = setInterval(tickElapsed, 1000)
    } else {
      if (elapsedTimer.current) clearInterval(elapsedTimer.current)
      if (recordingState === 'idle') resetElapsed()
    }
    return () => {
      if (elapsedTimer.current) clearInterval(elapsedTimer.current)
    }
  }, [recordingState])

  // Backend events and transcript wiring
  useEffect(() => {
    window.opennode.onBackendReady(() => {
      setBackendStatus('ready')
      // Load sessions now that backend is ready
      window.opennode.getSessions().then(setSessions).catch(console.error)
    })

    window.opennode.onStatus((data) => {
      setModelLoaded(data.model_loaded)
      setGpuAvailable(data.gpu_available)
    })

    window.opennode.onPartialTranscript((data) => {
      setPartialText(data.text)
    })

    window.opennode.onFinalTranscript((data) => {
      addTranscript({
        id: `${data.chunk_id}-${data.start_ms}`,
        text: data.text,
        speaker: data.speaker,
        isPartial: false,
        startMs: data.start_ms,
        confidence: data.confidence,
      })
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

    // Check if backend is already running (e.g. app reload / hot reload)
    window.opennode.getBackendStatus().then((status) => {
      if (status?.ready) {
        setBackendStatus('ready')
        window.opennode.getSessions().then(setSessions).catch(console.error)
      }
    }).catch(() => {})

    return () => {
      window.opennode.removeAllListeners('backend:ready')
      window.opennode.removeAllListeners('status')
      window.opennode.removeAllListeners('transcript:partial')
      window.opennode.removeAllListeners('transcript:final')
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
    <div className="flex h-screen bg-gray-900 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'live' && <LiveSession />}
        {currentView === 'session' && <SessionView />}
        {currentView === 'settings' && <Settings />}
      </main>
    </div>
  )
}
