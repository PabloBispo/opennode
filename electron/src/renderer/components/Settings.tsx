import React, { useState, useEffect } from 'react'
import type { AppSettings, SystemInfo } from '../../shared/types'
import { SettingRow } from './SettingRow'

// ─── Types ────────────────────────────────────────────────────────────────────

type Tab = 'general' | 'audio' | 'models' | 'overlay' | 'storage' | 'about'

interface TabProps {
  settings: AppSettings
  update: (partial: Partial<AppSettings>) => Promise<void>
}

// ─── Shared control styles ────────────────────────────────────────────────────

const selectClass =
  'bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500'

const checkboxClass = 'h-4 w-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500'

// ─── Tab: General ─────────────────────────────────────────────────────────────

function GeneralTab({ settings, update }: TabProps) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        General
      </h2>

      <SettingRow
        label="Language"
        description="Language used for transcription. 'Auto' detects language automatically."
      >
        <select
          className={selectClass}
          value={settings.language}
          onChange={(e) => update({ language: e.target.value })}
        >
          <option value="auto">Auto-detect</option>
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="it">Italian</option>
          <option value="pt">Portuguese</option>
          <option value="zh">Chinese</option>
          <option value="ja">Japanese</option>
          <option value="ko">Korean</option>
          <option value="ru">Russian</option>
          <option value="ar">Arabic</option>
          <option value="hi">Hindi</option>
        </select>
      </SettingRow>

      <SettingRow
        label="Theme"
        description="Controls the visual appearance of the application."
      >
        <select
          className={selectClass}
          value={settings.theme}
          onChange={(e) => update({ theme: e.target.value as AppSettings['theme'] })}
        >
          <option value="system">System</option>
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>
      </SettingRow>
    </div>
  )
}

// ─── Tab: Audio ───────────────────────────────────────────────────────────────

function AudioTab({ settings, update }: TabProps) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        Audio
      </h2>

      <SettingRow
        label="Capture source"
        description="Where audio is captured from during a session."
      >
        <select
          className={selectClass}
          value={settings.capture_source}
          onChange={(e) =>
            update({ capture_source: e.target.value as AppSettings['capture_source'] })
          }
        >
          <option value="system">System audio</option>
          <option value="microphone">Microphone</option>
          <option value="both">Both</option>
        </select>
      </SettingRow>
    </div>
  )
}

// ─── Tab: Models ──────────────────────────────────────────────────────────────

function ModelsTab({ settings, update }: TabProps) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        ASR Model
      </h2>

      <SettingRow
        label="ASR engine"
        description="Speech recognition model to use. Parakeet is GPU-accelerated and recommended."
      >
        <select
          className={selectClass}
          value={settings.asr_engine}
          onChange={(e) =>
            update({ asr_engine: e.target.value as AppSettings['asr_engine'] })
          }
        >
          <option value="parakeet">NVIDIA Parakeet (recommended)</option>
          <option value="whisper">Faster-Whisper (fallback)</option>
          <option value="onnx">ONNX (experimental)</option>
        </select>
      </SettingRow>

      <SettingRow
        label="Speaker diarization"
        description="Identify who is speaking. Requires additional VRAM."
      >
        <input
          type="checkbox"
          className={checkboxClass}
          checked={settings.enable_diarization}
          onChange={(e) => update({ enable_diarization: e.target.checked })}
        />
      </SettingRow>

      {settings.enable_diarization && (
        <SettingRow
          label="Max speakers"
          description="Maximum number of distinct speakers to detect (1–20)."
        >
          <input
            type="number"
            min={1}
            max={20}
            className="w-20 bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
            value={settings.max_speakers}
            onChange={(e) => update({ max_speakers: parseInt(e.target.value, 10) || 1 })}
          />
        </SettingRow>
      )}

      <div className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
          Summarization
        </h2>

        <SettingRow
          label="Enable summarization"
          description="Generate a meeting summary and action items at end of session."
        >
          <input
            type="checkbox"
            className={checkboxClass}
            checked={settings.enable_summarization}
            onChange={(e) => update({ enable_summarization: e.target.checked })}
          />
        </SettingRow>

        {settings.enable_summarization && (
          <>
            <SettingRow
              label="Provider"
              description="LLM service used for summarization."
            >
              <select
                className={selectClass}
                value={settings.summarization_provider}
                onChange={(e) =>
                  update({
                    summarization_provider: e.target.value as AppSettings['summarization_provider'],
                  })
                }
              >
                <option value="ollama">Ollama (local)</option>
                <option value="api">External API</option>
              </select>
            </SettingRow>

            {settings.summarization_provider === 'ollama' && (
              <SettingRow
                label="Ollama model"
                description="Name of the locally installed Ollama model to use."
              >
                <input
                  type="text"
                  className="w-44 bg-gray-800 border border-gray-700 text-white text-sm rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={settings.ollama_model}
                  onChange={(e) => update({ ollama_model: e.target.value })}
                  placeholder="llama3.2"
                />
              </SettingRow>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ─── Tab: Overlay ─────────────────────────────────────────────────────────────

function OverlayTab({ settings, update }: TabProps) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        PiP Overlay
      </h2>

      <SettingRow
        label="Position"
        description="Corner of the screen where the overlay window is anchored."
      >
        <select
          className={selectClass}
          value={settings.overlay_position}
          onChange={(e) =>
            update({ overlay_position: e.target.value as AppSettings['overlay_position'] })
          }
        >
          <option value="top-right">Top right</option>
          <option value="top-left">Top left</option>
          <option value="bottom-right">Bottom right</option>
          <option value="bottom-left">Bottom left</option>
        </select>
      </SettingRow>

      <SettingRow
        label="Opacity"
        description={`Transparency of the overlay window (${Math.round(settings.overlay_opacity * 100)}%).`}
      >
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={0.5}
            max={1.0}
            step={0.05}
            value={settings.overlay_opacity}
            onChange={(e) => update({ overlay_opacity: parseFloat(e.target.value) })}
            className="w-32 accent-blue-500"
          />
          <span className="text-sm text-gray-300 w-10 text-right">
            {Math.round(settings.overlay_opacity * 100)}%
          </span>
        </div>
      </SettingRow>
    </div>
  )
}

// ─── Tab: Storage ─────────────────────────────────────────────────────────────

function StorageTab() {
  const dataDir =
    typeof process !== 'undefined'
      ? `${process.env.HOME ?? '~'}/.opennode`
      : '~/.opennode'

  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        Storage
      </h2>

      <SettingRow
        label="Data directory"
        description="All recordings, transcripts, and models are stored here."
      >
        <span className="text-sm text-gray-400 font-mono">{dataDir}</span>
      </SettingRow>

      <SettingRow
        label="Save audio files"
        description="Keep raw audio recordings on disk after a session ends."
      >
        {/* Storage settings are not yet in AppSettings — show as informational only */}
        <span className="text-xs text-gray-500 italic">Coming soon</span>
      </SettingRow>

      <SettingRow
        label="Retention period"
        description="Automatically delete sessions older than N days (0 = keep forever)."
      >
        <span className="text-xs text-gray-500 italic">Coming soon</span>
      </SettingRow>
    </div>
  )
}

// ─── Tab: About ───────────────────────────────────────────────────────────────

function AboutTab() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)

  useEffect(() => {
    window.opennode.getSystemInfo().then(setSystemInfo).catch(() => {})
  }, [])

  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
        About OpenNode
      </h2>

      <SettingRow label="Version">
        <span className="text-sm text-gray-300">0.1.0</span>
      </SettingRow>

      <div className="mt-6">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-4">
          System
        </h2>

        {systemInfo ? (
          <>
            <SettingRow label="Platform">
              <span className="text-sm text-gray-300">
                {systemInfo.platform} / {systemInfo.arch}
              </span>
            </SettingRow>

            <SettingRow label="RAM">
              <span className="text-sm text-gray-300">
                {(systemInfo.total_ram_mb / 1024).toFixed(1)} GB
              </span>
            </SettingRow>

            <SettingRow label="GPU">
              <span className="text-sm text-gray-300">
                {systemInfo.gpu_available
                  ? systemInfo.gpu_name
                    ? `${systemInfo.gpu_name}${systemInfo.gpu_vram_mb ? ` (${(systemInfo.gpu_vram_mb / 1024).toFixed(1)} GB)` : ''}`
                    : 'Available'
                  : 'Not detected'}
              </span>
            </SettingRow>
          </>
        ) : (
          <p className="text-sm text-gray-500">Loading system info…</p>
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">
          OpenNode is open-source software. Real-time transcription powered by NVIDIA Parakeet.
        </p>
      </div>
    </div>
  )
}

// ─── Settings (root) ──────────────────────────────────────────────────────────

/**
 * Settings panel with a tab bar for General, Audio, Models, Overlay, Storage, and About.
 * Settings are loaded via the preload IPC bridge and persisted on every change.
 */
export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('general')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    window.opennode.getSettings().then(setSettings).catch(() => {})
  }, [])

  const update = async (partial: Partial<AppSettings>) => {
    const updated = await window.opennode.updateSettings(partial)
    setSettings(updated)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (!settings) {
    return <div className="p-8 text-gray-400">Loading settings…</div>
  }

  const tabs: Tab[] = ['general', 'audio', 'models', 'overlay', 'storage', 'about']

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Tab bar */}
      <div className="flex border-b border-gray-700 px-4">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium capitalize transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Saved confirmation toast */}
      {saved && (
        <div className="mx-4 mt-4 px-4 py-2 bg-green-900/50 border border-green-700 rounded text-green-400 text-sm">
          Settings saved
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'general' && <GeneralTab settings={settings} update={update} />}
        {activeTab === 'audio' && <AudioTab settings={settings} update={update} />}
        {activeTab === 'models' && <ModelsTab settings={settings} update={update} />}
        {activeTab === 'overlay' && <OverlayTab settings={settings} update={update} />}
        {activeTab === 'storage' && <StorageTab />}
        {activeTab === 'about' && <AboutTab />}
      </div>
    </div>
  )
}
