import React, { createContext, useEffect, useState } from 'react'
import type { AuthContextType, LoginRequest, UserResponse, UserRole } from '../types/auth'
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  loginStaff,
  getCurrentUserProfile,
} from '../services/api'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [token, setToken] = useState<string | null>(getAuthToken)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Validate existing session on application boot
  useEffect(() => {
    let isMounted = true
    const initAuth = async () => {
      const storedToken = getAuthToken()
      if (!storedToken) {
        if (isMounted) {
          setIsLoading(false)
        }
        return
      }

      try {
        const profile = await getCurrentUserProfile()
        if (isMounted) {
          if (profile && profile.is_active) {
            setUser(profile)
            setToken(storedToken)
          } else {
            clearAuthToken()
            setUser(null)
            setToken(null)
          }
        }
      } catch {
        // Token expired or invalid on backend
        if (isMounted) {
          clearAuthToken()
          setUser(null)
          setToken(null)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    initAuth()
    return () => {
      isMounted = false
    }
  }, [])

  const login = async (credentials: LoginRequest): Promise<UserResponse> => {
    setIsLoading(true)
    try {
      const resp = await loginStaff(credentials)
      setAuthToken(resp.access_token)
      setToken(resp.access_token)
      setUser(resp.user)
      return resp.user
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    clearAuthToken()
    setToken(null)
    setUser(null)
  }

  const refreshProfile = async (): Promise<void> => {
    try {
      const profile = await getCurrentUserProfile()
      if (profile && profile.is_active) {
        setUser(profile)
      } else {
        logout()
      }
    } catch {
      logout()
    }
  }

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    role: (user?.role as UserRole) ?? null,
    login,
    logout,
    refreshProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export { AuthContext }
