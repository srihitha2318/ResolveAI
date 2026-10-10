import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeProvider } from '../context/ThemeContext'
import { useTheme } from '../hooks/useTheme'
import { ThemeToggle } from '../components/common/ThemeToggle'

const TestConsumer = () => {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <span data-testid="current-theme">{theme}</span>
      <button onClick={toggleTheme}>Toggle</button>
    </div>
  )
}

describe('Theme System', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('defaults to light theme when no storage preference exists', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('toggles theme to dark and adds dark class to documentElement', () => {
    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    )

    const button = screen.getByText('Toggle')
    fireEvent.click(button)

    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('resolveai-theme')).toBe('dark')
  })

  it('persists and restores theme preference from localStorage', () => {
    localStorage.setItem('resolveai-theme', 'dark')

    render(
      <ThemeProvider>
        <TestConsumer />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('renders ThemeToggle button with accessible labels', () => {
    render(
      <ThemeProvider>
        <ThemeToggle showLabel />
      </ThemeProvider>
    )

    const toggleBtn = screen.getByRole('button', { name: /switch to dark mode/i })
    expect(toggleBtn).toBeInTheDocument()

    fireEvent.click(toggleBtn)
    expect(screen.getByRole('button', { name: /switch to light mode/i })).toBeInTheDocument()
  })
})
