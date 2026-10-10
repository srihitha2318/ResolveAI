import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { ProtectedRoute } from '../components/layout/ProtectedRoute'
import * as api from '../services/api'

describe('Protected Routes & RBAC Guards', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('redirects unauthenticated users to /login', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/supervisor']}>
          <Routes>
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={['tier2_supervisor', 'senior_supervisor']}>
                  <div>Secret Supervisor Area</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div>Login Page Target</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Login Page Target')).toBeInTheDocument()
      expect(screen.queryByText('Secret Supervisor Area')).not.toBeInTheDocument()
    })
  })

  it('renders protected component when user has required role', async () => {
    sessionStorage.setItem('resolveai_staff_token', 'token-alice')
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/supervisor']}>
          <Routes>
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={['tier2_supervisor', 'senior_supervisor']}>
                  <div>Supervisor Queue Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Supervisor Queue Content')).toBeInTheDocument()
    })
  })

  it('displays Access Denied when user role is not authorized', async () => {
    sessionStorage.setItem('resolveai_staff_token', 'token-charlie')
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 3,
      username: 'agent_charlie',
      full_name: 'Charlie Agent',
      role: 'frontline_agent',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/supervisor']}>
          <Routes>
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={['tier2_supervisor', 'senior_supervisor']}>
                  <div>Secret Supervisor Area</div>
                </ProtectedRoute>
              }
            />
            <Route path="/app" element={<div>Workspace Shell</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Access Denied/i)).toBeInTheDocument()
      expect(screen.getByText(/frontline_agent/i)).toBeInTheDocument()
      expect(screen.queryByText('Secret Supervisor Area')).not.toBeInTheDocument()
    })
  })
})
