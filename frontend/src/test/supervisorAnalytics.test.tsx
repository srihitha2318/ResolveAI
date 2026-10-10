import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { SupervisorAnalyticsPanel } from '../components/supervisor/SupervisorAnalyticsPanel'
import { CaseAuditHistoryModal } from '../components/supervisor/CaseAuditHistoryModal'
import * as api from '../services/api'
import type { AnalyticsOverviewResponse, CaseEventsListResponse } from '../types/analytics'

// Mock ResizeObserver for Recharts ResponsiveContainer
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const mockAnalytics: AnalyticsOverviewResponse = {
  total_cases: 48,
  open_cases: 12,
  in_progress_cases: 7,
  resolved_cases: 28,
  closed_cases: 8,
  escalated_cases: 3,
  pending_approvals: 3,
  approved_count: 24,
  rejected_count: 4,
  sla_breaches: 1,
  pending_clarifications: 2,
  category_distribution: [
    { category: 'defective_product', count: 18 },
    { category: 'delayed_shipping', count: 14 },
    { category: 'missing_items', count: 10 },
    { category: 'billing_dispute', count: 6 },
  ],
  status_distribution: [
    { status: 'resolved', count: 28 },
    { status: 'closed', count: 8 },
    { status: 'in_progress', count: 7 },
    { status: 'pending_review', count: 3 },
    { status: 'needs_information', count: 2 },
  ],
  recent_activity: [
    {
      case_number: 'CASE-2026-001',
      subject: 'Damaged tablet screen received on delivery',
      status: 'needs_information',
      created_at: '2026-10-09T10:00:00Z',
    },
    {
      case_number: 'CASE-2026-002',
      subject: 'High-value smartphone refund claim',
      status: 'pending_review',
      created_at: '2026-10-09T11:00:00Z',
    },
  ],
}

const mockAuditEvents: CaseEventsListResponse = {
  case_id: 1,
  events: [
    {
      id: 1,
      case_id: 1,
      event_type: 'case_opened',
      message: 'Workflow Initialized for customer complaint.',
      details_json: '{"order": "ORD-2026-001"}',
      created_at: '2026-10-09T10:00:00Z',
    },
    {
      id: 2,
      case_id: 1,
      event_type: 'clarification_requested',
      message: 'Serial number and unboxing photos requested from customer.',
      details_json: null,
      created_at: '2026-10-09T10:05:00Z',
    },
  ],
}

describe('Supervisor Analytics & Audit Trail Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('SupervisorAnalyticsPanel', () => {
    it('loads and displays operational KPI metric cards', async () => {
      vi.spyOn(api, 'getAnalyticsOverview').mockResolvedValue(mockAnalytics)

      render(<SupervisorAnalyticsPanel />)

      await waitFor(() => {
        expect(screen.getByText('Total Filed Cases')).toBeInTheDocument()
        expect(screen.getByText('48')).toBeInTheDocument()
        expect(screen.getByText('Pending Approvals')).toBeInTheDocument()
        expect(screen.getByText('Awaiting Information')).toBeInTheDocument()
        expect(screen.getByText('SLA Breaches')).toBeInTheDocument()
      })
    })

    it('renders recent case activity table with customer references', async () => {
      vi.spyOn(api, 'getAnalyticsOverview').mockResolvedValue(mockAnalytics)

      render(<SupervisorAnalyticsPanel />)

      await waitFor(() => {
        expect(screen.getByText('Recent Support Case Activity')).toBeInTheDocument()
        expect(screen.getByText('CASE-2026-001')).toBeInTheDocument()
        expect(screen.getByText('Damaged tablet screen received on delivery')).toBeInTheDocument()
        expect(screen.getByText('CASE-2026-002')).toBeInTheDocument()
      })
    })

    it('handles refresh button click to reload metrics', async () => {
      const getOverviewSpy = vi.spyOn(api, 'getAnalyticsOverview').mockResolvedValue(mockAnalytics)

      render(<SupervisorAnalyticsPanel />)

      await waitFor(() => {
        expect(screen.getByText('Total Filed Cases')).toBeInTheDocument()
      })

      const refreshBtn = screen.getByRole('button', { name: /Refresh Metrics/i })
      fireEvent.click(refreshBtn)

      expect(getOverviewSpy).toHaveBeenCalledTimes(2)
    })

    it('displays error state when analytics fetch fails', async () => {
      vi.spyOn(api, 'getAnalyticsOverview').mockRejectedValue(new Error('Failed to load operational metrics'))

      render(<SupervisorAnalyticsPanel />)

      await waitFor(() => {
        expect(screen.getByText('Failed to load operational metrics')).toBeInTheDocument()
      })
    })
  })

  describe('CaseAuditHistoryModal', () => {
    it('loads and displays chronological audit events with event badges', async () => {
      vi.spyOn(api, 'getCaseAuditEvents').mockResolvedValue(mockAuditEvents)
      const onClose = vi.fn()

      render(
        <CaseAuditHistoryModal
          isOpen={true}
          caseIdentifier="CASE-2026-001"
          caseNumber="CASE-2026-001"
          onClose={onClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Audit History & Event Trail — CASE-2026-001/i)).toBeInTheDocument()
        expect(screen.getByText('Workflow Initialized for customer complaint.')).toBeInTheDocument()
        expect(screen.getByText('Serial number and unboxing photos requested from customer.')).toBeInTheDocument()
      })
    })

    it('displays empty state when case has no recorded audit events', async () => {
      vi.spyOn(api, 'getCaseAuditEvents').mockResolvedValue({
        case_id: 2,
        events: [],
      })
      const onClose = vi.fn()

      render(
        <CaseAuditHistoryModal
          isOpen={true}
          caseIdentifier="CASE-2026-002"
          caseNumber="CASE-2026-002"
          onClose={onClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('No audit events recorded for this case yet.')).toBeInTheDocument()
      })
    })

    it('calls onClose callback when Close button is clicked', async () => {
      vi.spyOn(api, 'getCaseAuditEvents').mockResolvedValue(mockAuditEvents)
      const onClose = vi.fn()

      render(
        <CaseAuditHistoryModal
          isOpen={true}
          caseIdentifier="CASE-2026-001"
          caseNumber="CASE-2026-001"
          onClose={onClose}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/Audit History & Event Trail — CASE-2026-001/i)).toBeInTheDocument()
      })

      const closeButtons = screen.getAllByRole('button', { name: /Close/i })
      fireEvent.click(closeButtons[0])

      expect(onClose).toHaveBeenCalled()
    })
  })
})
