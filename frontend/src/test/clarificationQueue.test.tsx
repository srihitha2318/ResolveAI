import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import { AuthProvider } from '../context/AuthContext'
import { ClarificationQueueTable } from '../components/agent/ClarificationQueueTable'
import * as api from '../services/api'
import type { PendingClarificationItem } from '../types/workflow'
import { ApiError } from '../types/api'

const mockClarifications: PendingClarificationItem[] = [
  {
    thread_id: 'thread-clarify-111-alpha',
    case_id: 101,
    case_number: 'CAS-2026-0101',
    customer_id: 5,
    order_number: null,
    complaint_text: 'Items missing from shipment',
    missing_information: ['order_number', 'item_sku'],
    clarification_details: {
      order_number: 'Order number is required to look up seller invoice',
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    thread_id: 'thread-clarify-222-beta',
    case_id: 102,
    case_number: 'CAS-2026-0102',
    customer_id: 8,
    order_number: 'ORD-2026-088',
    complaint_text: 'Defect in cotton kurta',
    missing_information: ['damage_photos'],
    clarification_details: {
      damage_photos: 'Required for seller dispute resolution',
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

describe('ClarificationQueueTable', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    )
  }

  it('loads and renders clarification items in queue table', async () => {
    vi.spyOn(api, 'getPendingClarifications').mockResolvedValue({
      total_count: 2,
      limit: 50,
      offset: 0,
      items: mockClarifications,
    })

    renderWithProviders(<ClarificationQueueTable />)

    await waitFor(() => {
      expect(screen.getByText('CAS-2026-0101')).toBeInTheDocument()
      expect(screen.getByText('CAS-2026-0102')).toBeInTheDocument()
      expect(screen.getByText('order_number')).toBeInTheDocument()
      expect(screen.getByText('damage_photos')).toBeInTheDocument()
    })
  })

  it('renders empty queue state when no pending clarifications exist', async () => {
    vi.spyOn(api, 'getPendingClarifications').mockResolvedValue({
      total_count: 0,
      limit: 50,
      offset: 0,
      items: [],
    })

    renderWithProviders(<ClarificationQueueTable />)

    await waitFor(() => {
      expect(screen.getByText(/No Paused Clarifications/i)).toBeInTheDocument()
    })
  })

  it('filters table rows using search filter input', async () => {
    vi.spyOn(api, 'getPendingClarifications').mockResolvedValue({
      total_count: 2,
      limit: 50,
      offset: 0,
      items: mockClarifications,
    })

    renderWithProviders(<ClarificationQueueTable />)

    await waitFor(() => {
      expect(screen.getByText('CAS-2026-0101')).toBeInTheDocument()
      expect(screen.getByText('CAS-2026-0102')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/Filter by thread, case, order/i)
    fireEvent.change(searchInput, { target: { value: '0102' } })

    expect(screen.queryByText('CAS-2026-0101')).not.toBeInTheDocument()
    expect(screen.getByText('CAS-2026-0102')).toBeInTheDocument()
  })

  it('displays error alert when API call fails', async () => {
    vi.spyOn(api, 'getPendingClarifications').mockRejectedValue(
      new ApiError('Service unavailable', 503)
    )

    renderWithProviders(<ClarificationQueueTable />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Service unavailable/i)
    })
  })
})
