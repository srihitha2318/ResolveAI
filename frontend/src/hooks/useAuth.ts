import { useContext } from 'react'
import { AuthContext } from '../context/AuthContext'
import type { AuthContextType } from '../types/auth'

/**
 * Hook to consume authentication context with safety check
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
