import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { AuthProvider } from '../context/AuthContext'
import { ApprovalDetailModal } from '../components/supervisor/ApprovalDetailModal'
import * as api from '../services/api'
import type { ApprovalDetailResponse } from '../types/workflow'

const mockStandardDetail: ApprovalDetailResponse = {
  id: 10,
  case_id: 101,
  case_number: 'CASE-2026-010',
  thread_id: 'thread-std-10',
  requested_action: 'replacement',
  status: 'pending',
  workflow_status: 'pending_review',
  justification: 'Damaged item reported with photographic evidence.',
  proposed_resolution: 'Dispatch replacement unit.',
  policy_evidence: 'Clause 4.1: Eligible for replacement within 7 days.',
  reviewer_id: null,
  decision_reason: null,
  decision_timestamp: null,
  expires_at: new Date(Date.now() + 1000 * 60 * 60 * 4).toISOString(),
  sla_priority: 'standard',
  required_role: 'tier2_supervisor',
  is_expired: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  case: {
    id: 101,
    case_number: 'CASE-2026-010',
    subject: 'Damaged Product',
    complaint_text: 'The box was torn and the product cracked.',
    status: 'in_progress',
    priority: 'standard',
  },
  order: {
    order_number: 'ORD-2026-010',
    product_name: 'Wireless Headphones',
    total_amount: 450000, // ₹4,500.00
    currency: 'INR',
    delivery_status: 'delivered',
  },
  customer: {
    name: 'Ananya Roy',
    email: 'ananya@example.com',
  },
}

const mockExpiredDetail: ApprovalDetailResponse = {
  ...mockStandardDetail,
  id: 20,
  case_id: 102,
  case_number: 'CASE-2026-020',
  thread_id: 'thread-exp-20',
  expires_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
  is_expired: true,
}

const mockHighValueDetail: ApprovalDetailResponse = {
  ...mockStandardDetail,
  id: 30,
  case_id: 103,
  case_number: 'CASE-2026-030',
  thread_id: 'thread-high-30',
  order: {
    order_number: 'ORD-2026-030',
    product_name: 'Gaming Laptop',
    total_amount: 8500000, // ₹85,000.00 (Exceeds ₹25,000)
    currency: 'INR',
    delivery_status: 'delivered',
  },
}

describe('Approval Detail Modal & Decision Controls', () => {
  beforeEach(() => {
    sessionStorage.clear()
    sessionStorage.setItem('resolveai_staff_token', 'valid-token')
    vi.restoreAllMocks()
    window.confirm = vi.fn().mockReturnValue(true)
  })

  it('renders case facts, order info, and policy evidence', async () => {
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getApprovalDetails').mockResolvedValue(mockStandardDetail)

    render(
      <AuthProvider>
        <ApprovalDetailModal
          isOpen={true}
          threadId="thread-std-10"
          onClose={() => {}}
          onDecisionSuccess={() => {}}
        />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Ananya Roy')).toBeInTheDocument()
      expect(screen.getByText('ORD-2026-010')).toBeInTheDocument()
      expect(screen.getByText('Wireless Headphones')).toBeInTheDocument()
      expect(screen.getByText(/Clause 4.1/i)).toBeInTheDocument()
    })
  })

  it('disables Approve button for Tier 2 when claim is High-Value (> ₹25,000)', async () => {
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getApprovalDetails').mockResolvedValue(mockHighValueDetail)

    render(
      <AuthProvider>
        <ApprovalDetailModal
          isOpen={true}
          threadId="thread-high-30"
          onClose={() => {}}
          onDecisionSuccess={() => {}}
        />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/High-Value Claim Threshold Exceeded/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Approve Resolution/i })).toBeDisabled()
    })
  })

  it('requires Senior Supervisor SLA override checkbox before enabling decision buttons on expired cases', async () => {
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 2,
      username: 'senior_bob',
      full_name: 'Bob Senior',
      role: 'senior_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getApprovalDetails').mockResolvedValue(mockExpiredDetail)

    render(
      <AuthProvider>
        <ApprovalDetailModal
          isOpen={true}
          threadId="thread-exp-20"
          onClose={() => {}}
          onDecisionSuccess={() => {}}
        />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Target SLA Deadline Breached/i)).toBeInTheDocument()
    })

    // Initially disabled without override
    const approveBtn = screen.getByRole('button', { name: /Approve Resolution/i })
    expect(approveBtn).toBeDisabled()

    // Check the Senior Override checkbox
    const overrideCheckbox = screen.getByLabelText(/Enable Senior Supervisor SLA Override/i)
    fireEvent.click(overrideCheckbox)

    // Now enabled
    expect(approveBtn).not.toBeDisabled()
  })

  it('executes approval decision and triggers success callback', async () => {
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getApprovalDetails').mockResolvedValue(mockStandardDetail)
    const approveSpy = vi.spyOn(api, 'approveWorkflow').mockResolvedValue({
      id: 10,
      case_id: 101,
      thread_id: 'thread-std-10',
      status: 'approved',
      workflow_status: 'completed',
      reviewer_id: 'supervisor_alice',
      decision_reason: 'Approved via Supervisor Command Dashboard',
      decision_timestamp: new Date().toISOString(),
    })

    const onDecisionSuccess = vi.fn()

    render(
      <AuthProvider>
        <ApprovalDetailModal
          isOpen={true}
          threadId="thread-std-10"
          onClose={() => {}}
          onDecisionSuccess={onDecisionSuccess}
        />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Approve Resolution/i })).not.toBeDisabled()
    })

    fireEvent.click(screen.getByRole('button', { name: /Approve Resolution/i }))

    await waitFor(() => {
      expect(approveSpy).toHaveBeenCalledWith(
        'thread-std-10',
        expect.objectContaining({
          reviewer_id: 'supervisor_alice',
          override_expired: false,
        })
      )
      expect(onDecisionSuccess).toHaveBeenCalled()
    })
  })

  it('requires a mandatory reason before submitting rejection', async () => {
    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 1,
      username: 'supervisor_alice',
      full_name: 'Alice Supervisor',
      role: 'tier2_supervisor',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getApprovalDetails').mockResolvedValue(mockStandardDetail)
    const rejectSpy = vi.spyOn(api, 'rejectWorkflow').mockResolvedValue({
      id: 10,
      case_id: 101,
      thread_id: 'thread-std-10',
      status: 'rejected',
      workflow_status: 'rejected',
      reviewer_id: 'supervisor_alice',
      decision_reason: 'Return window was exceeded by 14 days.',
      decision_timestamp: new Date().toISOString(),
    })

    const onDecisionSuccess = vi.fn()

    render(
      <AuthProvider>
        <ApprovalDetailModal
          isOpen={true}
          threadId="thread-std-10"
          onClose={() => {}}
          onDecisionSuccess={onDecisionSuccess}
        />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Reject$/i })).toBeInTheDocument()
    })

    // Click Reject to open rejection mode
    fireEvent.click(screen.getByRole('button', { name: /^Reject$/i }))

    expect(screen.getByText(/Operational Rejection Reason \(Mandatory\)\*/i)).toBeInTheDocument()
    const confirmBtn = screen.getByRole('button', { name: /Confirm Rejection/i })
    expect(confirmBtn).toBeDisabled()

    // Type rejection reason
    const textarea = screen.getByPlaceholderText(/Explain why this resolution is being rejected/i)
    fireEvent.change(textarea, { target: { value: 'Return window was exceeded by 14 days.' } })

    expect(confirmBtn).not.toBeDisabled()
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(rejectSpy).toHaveBeenCalledWith(
        'thread-std-10',
        expect.objectContaining({
          reviewer_id: 'supervisor_alice',
          reason: 'Return window was exceeded by 14 days.',
        })
      )
      expect(onDecisionSuccess).toHaveBeenCalled()
    })
  })
})
