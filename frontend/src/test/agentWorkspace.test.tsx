import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import { AuthProvider } from '../context/AuthContext'
import { AgentWorkspacePage } from '../pages/AgentWorkspacePage'
import { ComplaintProcessingForm } from '../components/agent/ComplaintProcessingForm'
import { InvestigationResultsPanel } from '../components/agent/InvestigationResultsPanel'
import * as api from '../services/api'
import type { WorkflowResolveResponse } from '../types/workflow'
import { ApiError } from '../types/api'

const mockCompletedWorkflow: WorkflowResolveResponse = {
  workflow_id: 'wf-test-uuid-1234',
  thread_id: 'thread-checkpoint-abc-567',
  case_id: 42,
  case_number: 'CAS-2026-0042',
  status: 'completed',
  current_stage: 'finalized',
  complaint_analysis: {
    category: 'electronics',
    main_issue: 'Damaged smartphone screen',
    desired_outcome: 'replacement',
    order_number: 'ORD-2026-001',
    image_relevant: true,
    additional_info_required: false,
    analysis_method: 'rule_based',
    limitations: null,
  },
  order_investigation: {
    order_exists: true,
    order_number: 'ORD-2026-001',
    order_details: {
      id: 1,
      order_number: 'ORD-2026-001',
      product_name: 'Flagship Smartphone Pro',
      order_status: 'delivered',
      delivery_status: 'delivered',
      order_date: '2026-09-01T10:00:00Z',
      expected_delivery_date: '2026-09-05T10:00:00Z',
      delivered_at: '2026-09-05T10:00:00Z',
      total_amount: 1999900,
      currency: 'INR',
      customer_id: 10,
      seller_id: 'SELLER-001',
      category: 'electronics',
      total_amount_formatted: '₹19,999.00',
    },
    delivery_summary: 'Delivered within standard window',
    previous_cases: [],
    refund_status: 'not_recorded',
    missing_information: [],
    limitations: 'Database records verified',
  },
  policy_evidence: {
    query: 'damaged smartphone',
    passages: [
      {
        document_name: 'electronics_return_policy.md',
        passage: 'Damaged electronics must be reported within 48 hours for immediate replacement.',
        matched_terms: ['damaged', 'electronics'],
        line_number: 14,
        policy_id: 'POL-ELEC-001',
        scope: 'category',
      },
    ],
    found_relevant: true,
    retrieval_method: 'semantic_search',
    explanation: 'Electronics policy clause matches damaged condition.',
    policy_ids: ['POL-ELEC-001'],
    source_files: ['electronics_return_policy.md'],
    conflict_status: null,
    needs_review: false,
    insufficient_evidence: false,
  },
  retrieval_method: 'semantic_search',
  recommended_resolution: {
    recommendation_type: 'recommend_replacement_review',
    title: 'Replacement Recommended for In-Warranty Transit Damage',
    reasoning: 'Evidence meets electronics return clause 14 for prompt unit swap.',
    action_required: 'Dispatch replacement unit',
    human_approval_required: false,
    missing_information: [],
    evidence_used: ['POL-ELEC-001', 'ORD-2026-001'],
    method: 'rule_based',
  },
  verification_result: {
    verification_status: 'pass',
    is_valid: true,
    detected_issues: [],
    evidence_checked: ['order_status', 'delivery_date', 'policy_validity'],
    missing_evidence: [],
    required_next_step: 'proceed_to_execution',
  },
  needs_review: false,
  escalation_reason: null,
  supervisor_decision: null,
  missing_information: [],
  clarification_details: null,
  errors: [],
  retry_count: 0,
  events_recorded: [
    {
      event_type: 'complaint_analyzed',
      message: 'Complaint categorized as electronics transit damage',
    },
    {
      event_type: 'verification_passed',
      message: 'Independent verifier evaluated resolution as valid',
    },
  ],
  created_at: '2026-10-10T04:00:00Z',
  updated_at: '2026-10-10T04:00:05Z',
}

describe('Support Agent Workspace', () => {
  beforeEach(() => {
    sessionStorage.clear()
    sessionStorage.setItem('resolveai_staff_token', 'valid-agent-token')
    vi.restoreAllMocks()

    vi.spyOn(api, 'getCurrentUserProfile').mockResolvedValue({
      id: 3,
      username: 'agent_charlie',
      full_name: 'Charlie Frontline',
      role: 'frontline_agent',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    vi.spyOn(api, 'getSystemStatus').mockResolvedValue({
      app_name: 'ResolveAI',
      version: '0.1.0',
      database: 'connected',
    })
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

  describe('ComplaintProcessingForm Validation & Execution', () => {
    it('validates required complaint description before submitting', async () => {
      const submitMock = vi.fn()
      renderWithProviders(
        <ComplaintProcessingForm onSubmit={submitMock} isLoading={false} />
      )

      fireEvent.click(screen.getByRole('button', { name: /Execute AI Resolution/i }))

      expect(screen.getByRole('alert')).toHaveTextContent(
        /Please enter customer complaint text before submitting/i
      )
      expect(submitMock).not.toHaveBeenCalled()
    })

    it('submits valid complaint with optional order number and category hint', async () => {
      const submitMock = vi.fn().mockResolvedValue(undefined)
      renderWithProviders(
        <ComplaintProcessingForm onSubmit={submitMock} isLoading={false} />
      )

      fireEvent.change(screen.getByLabelText(/Customer Complaint Description/i), {
        target: { value: 'Screen arrived cracked out of the box.' },
      })
      fireEvent.change(screen.getByLabelText(/Order Number/i), {
        target: { value: 'ORD-2026-001' },
      })
      fireEvent.change(screen.getByLabelText(/Product Category Hint/i), {
        target: { value: 'electronics' },
      })

      fireEvent.click(screen.getByRole('button', { name: /Execute AI Resolution/i }))

      await waitFor(() => {
        expect(submitMock).toHaveBeenCalledTimes(1)
        expect(submitMock).toHaveBeenCalledWith(
          expect.objectContaining({
            complaint_text: 'Screen arrived cracked out of the box.',
            order_number: 'ORD-2026-001',
            category: 'electronics',
          })
        )
      })
    })

    it('prevents duplicate submissions while request is loading', () => {
      renderWithProviders(
        <ComplaintProcessingForm onSubmit={vi.fn()} isLoading={true} />
      )

      const submitBtn = screen.getByRole('button', { name: /Execute AI Resolution/i })
      expect(submitBtn).toBeDisabled()
      expect(submitBtn).toHaveAttribute('aria-busy', 'true')
    })
  })

  describe('InvestigationResultsPanel Rendering', () => {
    it('renders workflow identifiers, order investigation facts, and verifier result', () => {
      renderWithProviders(
        <InvestigationResultsPanel workflowResult={mockCompletedWorkflow} />
      )

      // Identifiers
      expect(screen.getByText(/Run ID: wf-test-uuid-1234/i)).toBeInTheDocument()
      expect(screen.getByText('CAS-2026-0042')).toBeInTheDocument()
      expect(screen.getByText(/Resolution Completed/i)).toBeInTheDocument()

      // Order investigation
      expect(screen.getByText('Flagship Smartphone Pro')).toBeInTheDocument()
      expect(screen.getByText('₹19,999.00')).toBeInTheDocument()

      // Verifier
      expect(screen.getByText(/Independent Verifier Audit/i)).toBeInTheDocument()
      expect(screen.getByText(/Passed Invariant Verification/i)).toBeInTheDocument()
      expect(screen.getByText('proceed_to_execution')).toBeInTheDocument()

      // Policy citations
      expect(screen.getByText('electronics_return_policy.md')).toBeInTheDocument()
      expect(screen.getAllByText(/POL-ELEC-001/i).length).toBeGreaterThan(0)
    })

    it('renders supervisor review required banner when workflow needs approval', () => {
      const reviewWorkflow: WorkflowResolveResponse = {
        ...mockCompletedWorkflow,
        status: 'needs_review',
        needs_review: true,
        escalation_reason: 'Order value exceeds standard auto-dispatch ceiling.',
      }

      renderWithProviders(
        <InvestigationResultsPanel workflowResult={reviewWorkflow} />
      )

      expect(screen.getByText(/Supervisor Approval Required/i)).toBeInTheDocument()
      expect(screen.getByText(/Order value exceeds standard auto-dispatch ceiling/i)).toBeInTheDocument()
      expect(screen.getByText(/Frontline support agents cannot approve their own requests/i)).toBeInTheDocument()
    })

    it('renders clarification required banner when missing customer info', () => {
      const clarificationWorkflow: WorkflowResolveResponse = {
        ...mockCompletedWorkflow,
        status: 'needs_information',
        missing_information: ['order_number', 'photo_evidence'],
        clarification_details: {
          order_number: 'Required to look up purchase record in database',
        },
      }

      renderWithProviders(
        <InvestigationResultsPanel workflowResult={clarificationWorkflow} />
      )

      expect(screen.getByText(/Additional Customer Information Required/i)).toBeInTheDocument()
      expect(screen.getByText('order_number')).toBeInTheDocument()
      expect(screen.getByText('photo_evidence')).toBeInTheDocument()
      expect(screen.getByText(/Required to look up purchase record in database/i)).toBeInTheDocument()
    })

    it('creates support ticket linked to case ID successfully', async () => {
      const ticketSpy = vi.spyOn(api, 'createTicketForCase').mockResolvedValue({
        ticket_id: 101,
        ticket_number: 'TCK-42-AB12CD',
        case_id: 42,
        category: 'electronics',
        status: 'open',
        created_at: '2026-10-10T04:10:00Z',
        is_duplicate: false,
      })

      renderWithProviders(
        <InvestigationResultsPanel workflowResult={mockCompletedWorkflow} />
      )

      const generateBtn = screen.getByRole('button', {
        name: /Generate Ticket for Case #42/i,
      })
      fireEvent.click(generateBtn)

      await waitFor(() => {
        expect(ticketSpy).toHaveBeenCalledWith(42, expect.objectContaining({ category: 'electronics' }))
        expect(screen.getByText('TCK-42-AB12CD')).toBeInTheDocument()
        expect(screen.getByText(/Support Ticket Successfully Linked/i)).toBeInTheDocument()
      })
    })

    it('displays error message when ticket creation fails', async () => {
      vi.spyOn(api, 'createTicketForCase').mockRejectedValue(
        new ApiError('Support case #42 is locked for modification.', 400)
      )

      renderWithProviders(
        <InvestigationResultsPanel workflowResult={mockCompletedWorkflow} />
      )

      const generateBtn = screen.getByRole('button', {
        name: /Generate Ticket for Case #42/i,
      })
      fireEvent.click(generateBtn)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          /Support case #42 is locked for modification/i
        )
      })
    })
  })

  describe('AgentWorkspacePage End-to-End Workflow Integration', () => {
    it('executes resolve workflow and displays full results panel', async () => {
      vi.spyOn(api, 'resolveComplaint').mockResolvedValue(mockCompletedWorkflow)

      renderWithProviders(<AgentWorkspacePage />)

      // Enter complaint text
      fireEvent.change(screen.getByLabelText(/Customer Complaint Description/i), {
        target: { value: 'My flagship smartphone arrived with shattered display.' },
      })

      // Submit workflow
      fireEvent.click(screen.getByRole('button', { name: /Execute AI Resolution/i }))

      await waitFor(() => {
        expect(screen.getByText('CAS-2026-0042')).toBeInTheDocument()
        expect(screen.getByText('Flagship Smartphone Pro')).toBeInTheDocument()
        expect(screen.getByText(/Resolution Completed/i)).toBeInTheDocument()
      })
    })

    it('displays workflow error banner on network or API failure', async () => {
      vi.spyOn(api, 'resolveComplaint').mockRejectedValue(
        new ApiError('Unable to connect to workflow engine.', 500)
      )

      renderWithProviders(<AgentWorkspacePage />)

      fireEvent.change(screen.getByLabelText(/Customer Complaint Description/i), {
        target: { value: 'My delivery was delayed.' },
      })
      fireEvent.click(screen.getByRole('button', { name: /Execute AI Resolution/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(
          /Unable to connect to workflow engine/i
        )
      })
    })
  })
})
