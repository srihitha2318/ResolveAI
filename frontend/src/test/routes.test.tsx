import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import { AuthProvider } from '../context/AuthContext'
import { LandingPage } from '../pages/LandingPage'
import { CustomerPortalPage } from '../pages/CustomerPortalPage'
import { LoginPage } from '../pages/LoginPage'
import { AppShellPage } from '../pages/AppShellPage'
import { NotFoundPage } from '../pages/NotFoundPage'

// Mock getSystemStatus to prevent relative URL parse errors in jsdom
vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api')
  return {
    ...actual,
    getSystemStatus: vi.fn().mockResolvedValue({
      app_name: 'ResolveAI',
      version: '0.1.0',
      database: 'connected',
    }),
  }
})

describe('Route Rendering', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.clearAllMocks()
  })

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[initialRoute]}>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/customer" element={<CustomerPortalPage />} />
              <Route path="/customer/complaint" element={<CustomerPortalPage />} />
              <Route path="/customer/track" element={<CustomerPortalPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/app" element={<AppShellPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    )
  }

  it('renders LandingPage at root route /', () => {
    renderWithRouter('/')
    expect(screen.getByRole('heading', { name: /AI-Powered Complaint Resolution/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Submit a Complaint/i })).toBeInTheDocument()
  })

  it('renders LoginPage placeholder at /login', () => {
    renderWithRouter('/login')
    expect(screen.getByText(/Staff Authentication Gateway/i)).toBeInTheDocument()
    expect(screen.getByText(/frontline_agent/i)).toBeInTheDocument()
  })

  it('renders AppShellPage foundation preview at /app', () => {
    renderWithRouter('/app')
    expect(screen.getByText(/Operational Application Shell/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Customer Experience/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Supervisor Command/i).length).toBeGreaterThan(0)
  })

  it('renders CustomerPortalPage at /customer', () => {
    renderWithRouter('/customer')
    expect(screen.getByRole('heading', { name: /Fair, Instant, & Policy-Verified Resolution/i })).toBeInTheDocument()
    expect(screen.getByText(/How ResolveAI Resolves Your Issue/i)).toBeInTheDocument()
  })

  it('renders CustomerPortalPage complaint tab at /customer/complaint', () => {
    renderWithRouter('/customer/complaint')
    expect(screen.getByRole('heading', { name: /File a Customer Complaint/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/Registered Email Address/i)).toBeInTheDocument()
  })

  it('renders NotFoundPage at unknown route /*', () => {
    renderWithRouter('/non-existent-page')
    expect(screen.getByText(/Error 404/i)).toBeInTheDocument()
    expect(screen.getByText(/Page Not Found/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Return to Home/i })).toBeInTheDocument()
  })
})
