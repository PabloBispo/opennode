import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SettingRow } from '../../renderer/components/SettingRow'

describe('SettingRow', () => {
  it('renders label and description', () => {
    render(
      <SettingRow label="Test Label" description="Test description">
        <input type="checkbox" />
      </SettingRow>
    )
    expect(screen.getByText('Test Label')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })

  it('renders children', () => {
    render(
      <SettingRow label="Label">
        <button>Click me</button>
      </SettingRow>
    )
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('renders without description', () => {
    render(
      <SettingRow label="No description">
        <span>content</span>
      </SettingRow>
    )
    expect(screen.getByText('No description')).toBeInTheDocument()
  })
})
