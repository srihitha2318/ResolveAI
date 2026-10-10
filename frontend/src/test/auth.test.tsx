import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import { AuthProvider } from '../context/AuthContext'
import { LoginPage } from '../pages/LoginPage'
import * as api from '../services/api'
import { ApiError } from '../types/api'

describe('Staff Authentication & Session Handling', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          {ui}
        </AuthProvider>
      </ThemeProvider>
    )
  }

  it('renders login form with username and password fields', () => {
    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    )

    expect(screen.getByLabelText(/Staff Username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Account Password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign In to Workspace/i })).toBeInTheDocument()
  })

  it('successfully logs in, stores token, and updates user profile', async () => {
    const mockUser = {
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor' as const,
      is_active: true,
      created_at: new Date().toISOString(),
    }

    vi.spyOn(api, 'loginStaff').mockResolvedValue({
      access_token: 'mock-jwt-token-xyz',
      token_type: 'bearer',
      user: mockUser,
    })

    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/supervisor" element={<div>Supervisor Console Screen</div>} />
        </Routes>
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/Staff Username/i), {
      target: { value: 'supervisor_alice' },
    })
    fireEvent.change(screen.getByLabelText(/Account Password/i), {
      target: { value: 'ValidPassword123!' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }))

    await waitFor(() => {
      expect(screen.getByText('Supervisor Console Screen')).toBeInTheDocument()
    })

    expect(sessionStorage.getItem('resolveai_staff_token')).toBe('mock-jwt-token-xyz')
  })

  it('displays error message on invalid credentials (401)', async () => {
    vi.spyOn(api, 'loginStaff').mockRejectedValue(
      new ApiError('Invalid username or password.', 401)
    )

    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByLabelText(/Staff Username/i), {
      target: { value: 'unknown_user' },
    })
    fireEvent.change(screen.getByLabelText(/Account Password/i), {
      target: { value: 'WrongPassword!' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Invalid username or password/i)
    })
  })

  it('validates empty inputs before submitting', async () => {
    const loginSpy = vi.spyOn(api, 'loginStaff')

    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/Please enter your staff username/i)
    expect(loginSpy).not.toHaveBeenCalled()
  })

  it('restores authenticated session when valid token exists in storage', async () => {
    sessionStorage.setItem('resolveai_staff_token', 'saved-valid-token')

    const mockProfile = {
      id: 2,
      username: 'senior_bob',
      full_name: 'Bob Senior',
      role: 'senior_supervisor' as const,
      is_active: true,
      created_at: new Date().toISOString(),
    }

    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue(mockProfile)

    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/supervisor" element={<div>Restored Senior Console</div>} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Restored Senior Console')).toBeInTheDocument()
    })
  })

  it('clears storage and resets state when session token is rejected by backend', async () => {
    sessionStorage.setItem('resolveai_staff_token', 'stale-expired-token')

    vi.spyOn(api, 'getCurrentUserProfile').mockRejectedValue(
      new ApiError('Token has expired', 401)
    )

    renderWithProviders(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(sessionStorage.getItem('resolveai_staff_token')).toBeNull()
      expect(screen.getByLabelText(/Staff Username/i)).toBeInTheDocument()
    })
  })
})
