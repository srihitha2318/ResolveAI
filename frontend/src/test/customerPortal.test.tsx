import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CustomerHero } from '../components/customer/CustomerHero'
import { CustomerComplaintForm } from '../components/customer/CustomerComplaintForm'
import { CustomerCaseTracker } from '../components/customer/CustomerCaseTracker'
import { CustomerClarificationModal } from '../components/customer/CustomerClarificationModal'
import * as api from '../services/api'
import type { WorkflowResolveResponse } from '../types/workflow'
import type { CustomerCaseDetail, CustomerAccessResponse } from '../types/customer'

describe('Customer Portal Components', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  describe('CustomerHero', () => {
    it('renders hero title, action buttons, and process steps', () => {
      const onSelectAction = vi.fn()
      render(
        <MemoryRouter>
          <CustomerHero onSelectAction={onSelectAction} />
        </MemoryRouter>
      )

      expect(screen.getByRole('heading', { name: /Fair, Instant, & Policy-Verified Resolution/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Submit a Complaint/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Track Existing Case/i })).toBeInTheDocument()
      expect(screen.getByText(/How ResolveAI Resolves Your Issue/i)).toBeInTheDocument()
      expect(screen.getByText(/Intake & Verification/i)).toBeInTheDocument()
      expect(screen.getByText(/Policy Matching & Independent Audit/i)).toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: /Submit a Complaint/i }))
      expect(onSelectAction).toHaveBeenCalledWith('complaint')

      fireEvent.click(screen.getByRole('button', { name: /Track Existing Case/i }))
      expect(onSelectAction).toHaveBeenCalledWith('track')
    })
  })

  describe('CustomerComplaintForm', () => {
    it('validates required email and complaint description before submitting', async () => {
      render(
        <MemoryRouter>
          <CustomerComplaintForm />
        </MemoryRouter>
      )

      const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i })
      fireEvent.click(submitBtn)

      expect(await screen.findByText(/Registered customer email is required/i)).toBeInTheDocument()
      expect(await screen.findByText(/Complaint description is required/i)).toBeInTheDocument()
    })

    it('submits complaint and displays case details on success', async () => {
      const mockResponse: WorkflowResolveResponse = {
        thread_id: 'thread-cust-123',
        status: 'completed',
        case_id: 42,
        case_number: 'CASE-2026-042',
        workflow_id: 'wf-cust-123',
        current_stage: 'completed',
        complaint_summary: 'Package marked delivered but damaged item received.',
        recommended_resolution: {
          title: 'Full Replacement Approved',
          action_required: 'replacement',
          reasoning: 'Damage occurred during transit within return window.',
          recommendation_type: 'replacement',
          evidence_used: ['Policy section 3.2 - transit damage guarantee'],
        },
      }

      vi.spyOn(api, 'resolveComplaint').mockResolvedValue(mockResponse)
      vi.spyOn(api, 'verifyCustomerAccess').mockResolvedValue({
        access_token: 'cust-token',
        token_type: 'bearer',
        customer_id: 1,
        customer_email: 'alice.chen@example.com',
        customer_name: 'Alice Chen',
        cases: [],
      })

      render(
        <MemoryRouter>
          <CustomerComplaintForm />
        </MemoryRouter>
      )

      const emailInput = screen.getByLabelText(/Registered Email Address/i)
      const orderInput = screen.getByPlaceholderText(/e\.g\. ORD-2026-001/i)
      const descInput = screen.getByLabelText(/Describe Your Issue in Detail/i)

      fireEvent.change(emailInput, { target: { value: 'alice.chen@example.com' } })
      fireEvent.change(orderInput, { target: { value: 'ORD-2026-001' } })
      fireEvent.change(descInput, { target: { value: 'The delivered electronic tablet had a cracked display screen on unboxing.' } })

      const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i })
      fireEvent.click(submitBtn)

      await waitFor(() => {
        expect(screen.getByText('Complaint Processed & Verified')).toBeInTheDocument()
        expect(screen.getByText('CASE-2026-042')).toBeInTheDocument()
        expect(screen.getByText('Full Replacement Approved')).toBeInTheDocument()
      })
    })

    it('handles pending review status accurately without claiming final resolution', async () => {
      const mockResponse: WorkflowResolveResponse = {
        thread_id: 'thread-cust-review',
        status: 'needs_review',
        case_id: 43,
        case_number: 'CASE-2026-043',
        workflow_id: 'wf-cust-review',
        current_stage: 'pending_supervisor_review',
        complaint_summary: 'High-value smartphone refund claim.',
      }

      vi.spyOn(api, 'resolveComplaint').mockResolvedValue(mockResponse)

      render(
        <MemoryRouter>
          <CustomerComplaintForm />
        </MemoryRouter>
      )

      const emailInput = screen.getByLabelText(/Registered Email Address/i)
      const descInput = screen.getByLabelText(/Describe Your Issue in Detail/i)

      fireEvent.change(emailInput, { target: { value: 'bob.martinez@example.com' } })
      fireEvent.change(descInput, { target: { value: 'Claiming refund for unopened smartphone returned yesterday.' } })

      const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i })
      fireEvent.click(submitBtn)

      await waitFor(() => {
        expect(screen.getByText('Pending Supervisor Review')).toBeInTheDocument()
        expect(screen.getByText(/This case requires supervisor authorization/i)).toBeInTheDocument()
      })
    })

    it('displays error banner when workflow submission fails', async () => {
      vi.spyOn(api, 'resolveComplaint').mockRejectedValue(new Error('Network gateway timeout'))

      render(
        <MemoryRouter>
          <CustomerComplaintForm />
        </MemoryRouter>
      )

      const emailInput = screen.getByLabelText(/Registered Email Address/i)
      const descInput = screen.getByLabelText(/Describe Your Issue in Detail/i)

      fireEvent.change(emailInput, { target: { value: 'alice.chen@example.com' } })
      fireEvent.change(descInput, { target: { value: 'Package was never received at the address.' } })

      const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i })
      fireEvent.click(submitBtn)

      await waitFor(() => {
        expect(screen.getByText('Network gateway timeout')).toBeInTheDocument()
      })
    })
  })

  describe('CustomerCaseTracker', () => {
    it('validates email field before verification', async () => {
      render(
        <MemoryRouter>
          <CustomerCaseTracker />
        </MemoryRouter>
      )

      const verifyBtn = screen.getByRole('button', { name: /View My Support Cases/i })
      fireEvent.click(verifyBtn)

      expect(await screen.findByText(/Please enter your registered email address/i)).toBeInTheDocument()
    })

    it('authenticates customer and displays case details', async () => {
      const mockVerifyResponse: CustomerAccessResponse = {
        access_token: 'cust-token-alice',
        token_type: 'bearer',
        customer_id: 1,
        customer_email: 'alice.chen@example.com',
        customer_name: 'Alice Chen',
        cases: [
          {
            case_number: 'CASE-2026-001',
            order_number: 'ORD-2026-001',
            product_name: 'Wireless Noise Canceling Headphones',
            subject: 'Damaged tablet screen on unboxing',
            status: 'in_progress',
            created_at: new Date().toISOString(),
            clarification_needed: true,
            thread_id: 'thread-clarify-001',
          },
        ],
      }

      const mockCaseDetail: CustomerCaseDetail = {
        case_number: 'CASE-2026-001',
        order_number: 'ORD-2026-001',
        product_name: 'Wireless Noise Canceling Headphones',
        order_status: 'delivered',
        delivery_status: 'delivered',
        subject: 'Damaged tablet screen on unboxing',
        complaint_text: 'Customer reports missing charging cable and warranty card.',
        status: 'in_progress',
        priority: 'medium',
        ticket_number: 'TICK-2026-001',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        clarification_needed: true,
        clarification_prompt: 'Please provide serial number located on the original box.',
        thread_id: 'thread-clarify-001',
        missing_fields: ['serial_number'],
      }

      vi.spyOn(api, 'verifyCustomerAccess').mockResolvedValue(mockVerifyResponse)
      vi.spyOn(api, 'getCustomerCaseDetail').mockResolvedValue(mockCaseDetail)

      render(
        <MemoryRouter>
          <CustomerCaseTracker />
        </MemoryRouter>
      )

      const emailInput = screen.getByLabelText(/Registered Email Address/i)
      const orderInput = screen.getByPlaceholderText(/ORD-2026-001 or CASE-2026-1001/i)

      fireEvent.change(emailInput, { target: { value: 'alice.chen@example.com' } })
      fireEvent.change(orderInput, { target: { value: 'ORD-2026-001' } })

      fireEvent.click(screen.getByRole('button', { name: /View My Support Cases/i }))

      await waitFor(() => {
        expect(screen.getByText('Alice Chen')).toBeInTheDocument()
        expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0)
        expect(screen.getByText('Customer reports missing charging cable and warranty card.')).toBeInTheDocument()
        expect(screen.getByText('Provide Information')).toBeInTheDocument()
      })
    })

    it('displays error on unauthorized or invalid ownership match', async () => {
      vi.spyOn(api, 'verifyCustomerAccess').mockRejectedValue(new Error('No matching customer order found with provided email and reference.'))

      render(
        <MemoryRouter>
          <CustomerCaseTracker />
        </MemoryRouter>
      )

      const emailInput = screen.getByLabelText(/Registered Email Address/i)
      const orderInput = screen.getByPlaceholderText(/ORD-2026-001 or CASE-2026-1001/i)

      fireEvent.change(emailInput, { target: { value: 'stranger@example.com' } })
      fireEvent.change(orderInput, { target: { value: 'ORD-2026-999' } })

      fireEvent.click(screen.getByRole('button', { name: /View My Support Cases/i }))

      await waitFor(() => {
        expect(screen.getByText(/No matching customer order found/i)).toBeInTheDocument()
      })
    })
  })

  describe('CustomerClarificationModal', () => {
    it('validates empty response input and submits clarification facts successfully', async () => {
      const onClarificationSubmitted = vi.fn()
      const onClose = vi.fn()

      vi.spyOn(api, 'submitCustomerClarification').mockResolvedValue({
        status: 'resumed',
        thread_id: 'thread-clarify-001',
        workflow_status: 'in_progress',
        message: 'Customer clarification incorporated and workflow resumed',
      })

      render(
        <CustomerClarificationModal
          isOpen={true}
          caseNumber="CASE-2026-001"
          threadId="thread-clarify-001"
          clarificationPrompt="Please provide serial number located on the original box."
          customerEmail="alice.chen@example.com"
          onClose={onClose}
          onClarificationSubmitted={onClarificationSubmitted}
        />
      )

      expect(screen.getByText('Provide Missing Customer Information')).toBeInTheDocument()
      expect(screen.getByText('Please provide serial number located on the original box.')).toBeInTheDocument()

      const submitBtn = screen.getByRole('button', { name: /Submit Clarification/i })
      fireEvent.click(submitBtn)

      expect(await screen.findByText(/Please provide at least one piece of clarification/i)).toBeInTheDocument()

      const textarea = screen.getByPlaceholderText(/Provide the missing context/i)
      fireEvent.change(textarea, { target: { value: 'Serial number on the bottom barcode is SN-8839201-B.' } })

      fireEvent.click(submitBtn)

      await waitFor(() => {
        expect(api.submitCustomerClarification).toHaveBeenCalledWith('thread-clarify-001', {
          additional_details: 'Serial number on the bottom barcode is SN-8839201-B.',
          customer_email: 'alice.chen@example.com',
          order_number: undefined,
        })
        expect(onClarificationSubmitted).toHaveBeenCalled()
      })
    })
  })
})
