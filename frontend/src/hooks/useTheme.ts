import { useContext } from 'react'
import { ThemeContext } from '../context/ThemeContext'
import type { ThemeContextType } from '../types/theme'

/**
 * Hook to consume theme context with safety check
 */
export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
