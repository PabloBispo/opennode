import React from 'react'

interface SettingRowProps {
  label: string
  description?: string
  children: React.ReactNode
}

/**
 * SettingRow — a single labelled row inside a settings section.
 * Renders the label (and optional description) on the left side and
 * the form control (passed as children) on the right side.
 */
export function SettingRow({ label, description, children }: SettingRowProps) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-gray-800">
      <div>
        <div className="text-sm font-medium text-white">{label}</div>
        {description && <div className="text-xs text-gray-400 mt-1">{description}</div>}
      </div>
      <div className="ml-8 flex-shrink-0">{children}</div>
    </div>
  )
}
