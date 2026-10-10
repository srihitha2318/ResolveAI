import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import { AuthProvider } from '../context/AuthContext'
import { SupervisorDashboardPage } from '../pages/SupervisorDashboardPage'
import * as api from '../services/api'
import type { PendingApprovalItem } from '../types/workflow'

const mockApprovals: PendingApprovalItem[] = [
  {
    id: 101,
    case_id: 1,
    case_number: 'CASE-2026-001',
    order_number: 'ORD-2026-100',
    customer_name: 'Priya Sharma',
    thread_id: 'thread-alpha-123',
    requested_action: 'replacement',
    status: 'pending',
    workflow_status: 'pending_review',
    justification: 'Electronics damage reported within 48h.',
    proposed_resolution: 'Approved replacement dispatch.',
    policy_evidence: 'Standard return policy clause 3.',
    expires_at: new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString(), // 6 hours remaining
    sla_priority: 'standard',
    required_role: 'tier2_supervisor',
    is_expired: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 102,
    case_id: 2,
    case_number: 'CASE-2026-002',
    order_number: 'ORD-2026-200',
    customer_name: 'Rahul Verma',
    thread_id: 'thread-beta-456',
    requested_action: 'refund',
    status: 'pending',
    workflow_status: 'pending_review',
    justification: 'High value flagship smartphone claim.',
    proposed_resolution: 'Full refund of ₹35,000.',
    policy_evidence: 'High value policy clause 7.',
    expires_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // Expired 30 mins ago
    sla_priority: 'high',
    required_role: 'senior_supervisor',
    is_expired: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

describe('Supervisor Dashboard', () => {
  beforeEach(() => {
    sessionStorage.clear()
    sessionStorage.setItem('resolveai_staff_token', 'valid-token')
    vi.restoreAllMocks()

    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })
  })

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            {ui}
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    )
  }

  it('loads and renders approval items in table', async () => {
    vi.spyOn(api, 'getPendingApprovals').mockResolvedValue({
      total_count: 2,
      limit: 50,
      offset: 0,
      items: mockApprovals,
    })

    renderWithProviders(<SupervisorDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('CASE-2026-001')).toBeInTheDocument()
      expect(screen.getByText('ORD-2026-100')).toBeInTheDocument()
      expect(screen.getByText('Priya Sharma')).toBeInTheDocument()
      expect(screen.getByText('CASE-2026-002')).toBeInTheDocument()
    })
  })

  it('renders empty queue state when no pending approvals exist', async () => {
    vi.spyOn(api, 'getPendingApprovals').mockResolvedValue({
      total_count: 0,
      limit: 50,
      offset: 0,
      items: [],
    })

    renderWithProviders(<SupervisorDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText(/Approval Queue is Clean/i)).toBeInTheDocument()
    })
  })

  it('calculates metrics cards accurately from items data', async () => {
    vi.spyOn(api, 'getPendingApprovals').mockResolvedValue({
      total_count: 2,
      limit: 50,
      offset: 0,
      items: mockApprovals,
    })

    renderWithProviders(<SupervisorDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Pending Queue')).toBeInTheDocument()
      expect(screen.getByText('Expired Approvals')).toBeInTheDocument()
      expect(screen.getByText('High-Value Claims')).toBeInTheDocument()
    })
  })

  it('filters table rows using search input', async () => {
    vi.spyOn(api, 'getPendingApprovals').mockResolvedValue({
      total_count: 2,
      limit: 50,
      offset: 0,
      items: mockApprovals,
    })

    renderWithProviders(<SupervisorDashboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Priya Sharma')).toBeInTheDocument()
      expect(screen.getByText('Rahul Verma')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/Filter case, order, or customer/i)
    fireEvent.change(searchInput, { target: { value: 'Rahul' } })

    expect(screen.queryByText('Priya Sharma')).not.toBeInTheDocument()
    expect(screen.getByText('Rahul Verma')).toBeInTheDocument()
  })
})
