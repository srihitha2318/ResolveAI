import React, { useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import {
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  XCircle,
  FileText,
  Package,
  BookOpen,
  Sparkles,
  Ticket,
  Clock,
  Layers,
  Info,
} from 'lucide-react'
import type {
  WorkflowResolveResponse,
  CreateTicketResponse,
} from '../../types/workflow'
import { createTicketForCase } from '../../services/api'
import { ApiError } from '../../types/api'
import { formatPaiseToINR } from '../../utils/currency'

export interface InvestigationResultsPanelProps {
  workflowResult: WorkflowResolveResponse
  onNewComplaint?: () => void
}

export const InvestigationResultsPanel: React.FC<InvestigationResultsPanelProps> = ({
  workflowResult,
  onNewComplaint,
}) => {
  const [ticketCategory, setTicketCategory] = useState(
    workflowResult.complaint_analysis?.category || 'general_inquiry'
  )
  const [isCreatingTicket, setIsCreatingTicket] = useState(false)
  const [createdTicket, setCreatedTicket] = useState<CreateTicketResponse | null>(null)
  const [ticketError, setTicketError] = useState<string | null>(null)

  const handleCreateTicket = async () => {
    if (!workflowResult.case_id) {
      setTicketError('No case ID associated with this workflow run. Ticket creation requires an active case ID.')
      return
    }

    setIsCreatingTicket(true)
    setTicketError(null)

    try {
      const ticketResp = await createTicketForCase(workflowResult.case_id, {
        category: ticketCategory.trim() || 'general_inquiry',
      })
      setCreatedTicket(ticketResp)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setTicketError(err.message || 'Failed to create support ticket.')
      } else {
        setTicketError('An unexpected error occurred while creating the ticket.')
      }
    } finally {
      setIsCreatingTicket(false)
    }
  }

  // Determine workflow status styling and label
  const renderStatusBadge = () => {
    switch (workflowResult.status) {
      case 'completed':
        return (
          <Badge variant="success" size="md" dot>
            Resolution Completed
          </Badge>
        )
      case 'needs_review':
        return (
          <Badge variant="pending" size="md" dot>
            Supervisor Review Required
          </Badge>
        )
      case 'needs_information':
        return (
          <Badge variant="neutral" size="md" dot>
            Awaiting Customer Clarification
          </Badge>
        )
      case 'rejected':
        return (
          <Badge variant="error" size="md" dot>
            Workflow Rejected
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="error" size="md" dot>
            Workflow Execution Failed
          </Badge>
        )
      default:
        return (
          <Badge variant="neutral" size="md">
            Status: {workflowResult.status}
          </Badge>
        )
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* 1. Header Overview Card */}
      <Card variant="elevated">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-mono text-gray-500 dark:text-gray-400">
                  Run ID: {workflowResult.workflow_id}
                </span>
                {renderStatusBadge()}
              </div>
              <CardTitle className="text-lg">
                Multi-Agent Investigation & Evaluation Summary
              </CardTitle>
              <CardDescription>
                Deterministic multi-agent execution results with independent verifier sign-off
              </CardDescription>
            </div>

            {onNewComplaint && (
              <Button
                variant="outline"
                size="sm"
                onClick={onNewComplaint}
                className="self-start sm:self-auto text-xs"
              >
                Process Another Case
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-lg bg-gray-50/80 dark:bg-dark-bg/60 border border-gray-200 dark:border-dark-border text-xs">
            <div>
              <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                Thread Checkpoint
              </span>
              <span className="font-mono text-gray-800 dark:text-gray-200 truncate block" title={workflowResult.thread_id || 'None'}>
                {workflowResult.thread_id ? workflowResult.thread_id.substring(0, 16) + '...' : 'Ephemeral'}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                Case Identifier
              </span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {workflowResult.case_number || (workflowResult.case_id ? `Case #${workflowResult.case_id}` : 'None created')}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                Current Execution Node
              </span>
              <span className="font-mono text-brand-forest dark:text-brand-sage font-semibold">
                {workflowResult.current_stage}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                Recovery Cycles
              </span>
              <span className="text-gray-800 dark:text-gray-200 font-mono">
                {workflowResult.retry_count} retries
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Critical Action Banners (Clarification or Supervisor Approval) */}
      {workflowResult.status === 'needs_review' && (
        <div
          className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 space-y-2"
          role="region"
          aria-label="Supervisor Review Banner"
        >
          <div className="flex items-center gap-2 font-bold text-sm">
            <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <span>Supervisor Approval Required — Action Paused at Checkpoint</span>
          </div>
          <p className="text-xs leading-relaxed">
            The AI recommendation requires operational supervisor authorization before final dispatch.
            {workflowResult.escalation_reason && (
              <span className="font-semibold block mt-1">
                Escalation Justification: {workflowResult.escalation_reason}
              </span>
            )}
          </p>
          <div className="text-[11px] text-amber-800/80 dark:text-amber-300/80 pt-1 border-t border-amber-200 dark:border-amber-800/60">
            <strong>Security Boundary:</strong> Frontline support agents cannot approve their own requests.
            Authorized Tier-2 or Senior Supervisors must review this thread in the{' '}
            <span className="font-semibold underline">Pending Approvals Queue</span>.
          </div>
        </div>
      )}

      {workflowResult.status === 'needs_information' && (
        <div
          className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-300 dark:border-blue-800 text-blue-900 dark:text-blue-200 space-y-2"
          role="region"
          aria-label="Clarification Required Banner"
        >
          <div className="flex items-center gap-2 font-bold text-sm">
            <HelpCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <span>Additional Customer Information Required</span>
          </div>
          <p className="text-xs leading-relaxed">
            The workflow has paused safely because required evidence could not be confirmed.
          </p>
          {workflowResult.missing_information && workflowResult.missing_information.length > 0 && (
            <div className="mt-2 space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-800 dark:text-blue-300">
                Missing Information Fields:
              </span>
              <ul className="list-disc pl-5 text-xs space-y-0.5">
                {workflowResult.missing_information.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px]">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {workflowResult.clarification_details && (
            <div className="p-2.5 rounded-lg bg-blue-100/60 dark:bg-blue-900/40 text-xs space-y-1 mt-2">
              <span className="font-semibold block text-[11px]">Clarification Instructions:</span>
              {Object.entries(workflowResult.clarification_details).map(([field, reason]) => (
                <div key={field} className="text-[11px]">
                  <strong className="font-mono">{field}:</strong> {reason}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 3. Section D: Recommended Resolution (Primary Focal Point) */}
      {workflowResult.recommended_resolution && (
        <Card variant="default">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                <CardTitle className="text-base">Proposed Resolution Recommendation</CardTitle>
              </div>
              <Badge
                variant={
                  workflowResult.recommended_resolution.human_approval_required
                    ? 'pending'
                    : 'success'
                }
                size="sm"
              >
                {workflowResult.recommended_resolution.recommendation_type}
              </Badge>
            </div>
            <CardDescription>
              {workflowResult.recommended_resolution.title}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-3 text-xs">
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-1.5">
              <span className="text-[10px] font-semibold uppercase text-gray-500 tracking-wider">
                Action Required
              </span>
              <p className="font-medium text-gray-800 dark:text-gray-200 text-xs">
                {workflowResult.recommended_resolution.action_required}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-semibold uppercase text-gray-500 tracking-wider block mb-1">
                Reasoning & Evidence Synthesis
              </span>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-xs">
                {workflowResult.recommended_resolution.reasoning}
              </p>
            </div>

            {workflowResult.recommended_resolution.evidence_used &&
              workflowResult.recommended_resolution.evidence_used.length > 0 && (
                <div>
                  <span className="text-[10px] font-semibold uppercase text-gray-500 tracking-wider block mb-1">
                    Citations Referenced
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {workflowResult.recommended_resolution.evidence_used.map((ev, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-gray-400 font-mono text-[11px]"
                      >
                        {ev}
                      </span>
                    ))}
                  </div>
                </div>
              )}

            <div className="p-2.5 rounded-lg bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-[11px] text-amber-900 dark:text-amber-300 flex items-start gap-2">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Operational Boundary:</strong> A proposed resolution is an AI recommendation, not a finalized disbursement. Financial compensations require formal supervisor review.
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 4. Section E: Independent Verifier Audit */}
      {workflowResult.verification_result && (
        <Card variant="default">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {workflowResult.verification_result.is_valid ? (
                  <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                )}
                <CardTitle className="text-base">Independent Verifier Audit</CardTitle>
              </div>
              <Badge
                variant={workflowResult.verification_result.is_valid ? 'success' : 'error'}
                size="sm"
              >
                Verifier: {workflowResult.verification_result.verification_status.toUpperCase()}
              </Badge>
            </div>
            <CardDescription>
              Factual consistency, policy citation validity, and boundary guard validation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-3 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                <span className="text-[10px] uppercase font-semibold text-gray-500 block">
                  Mandatory Next Step
                </span>
                <span className="font-medium text-gray-800 dark:text-gray-200 text-xs">
                  {workflowResult.verification_result.required_next_step}
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                <span className="text-[10px] uppercase font-semibold text-gray-500 block">
                  Safety Gate Evaluation
                </span>
                <span className="flex items-center gap-1.5 font-medium text-xs">
                  {workflowResult.verification_result.is_valid ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Passed Invariant Verification</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-3.5 h-3.5 text-rose-500" />
                      <span>Boundary Exception Detected</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            {workflowResult.verification_result.detected_issues &&
              workflowResult.verification_result.detected_issues.length > 0 && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800">
                  <span className="text-[11px] font-bold text-rose-900 dark:text-rose-200 block mb-1">
                    Detected Contradictions or Policy Issues:
                  </span>
                  <ul className="list-disc pl-5 space-y-1 text-rose-800 dark:text-rose-300 text-[11px]">
                    {workflowResult.verification_result.detected_issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
          </CardContent>
        </Card>
      )}

      {/* 5. Section A: Complaint Analysis & Section B: Order Investigation Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section A: Complaint Analysis */}
        {workflowResult.complaint_analysis && (
          <Card variant="default">
            <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                  <CardTitle className="text-base">Complaint Analysis</CardTitle>
                </div>
                <Badge variant="neutral" size="sm">
                  {workflowResult.complaint_analysis.category}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-3 text-xs">
              <div>
                <span className="text-[10px] font-semibold uppercase text-gray-500 block mb-0.5">
                  Main Issue Classified
                </span>
                <p className="text-gray-800 dark:text-gray-200 font-medium">
                  {workflowResult.complaint_analysis.main_issue}
                </p>
              </div>

              {workflowResult.complaint_analysis.desired_outcome && (
                <div>
                  <span className="text-[10px] font-semibold uppercase text-gray-500 block mb-0.5">
                    Customer Desired Outcome
                  </span>
                  <p className="text-gray-700 dark:text-gray-300">
                    {workflowResult.complaint_analysis.desired_outcome}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-600 dark:text-gray-400 pt-1">
                <div>
                  <span className="block text-gray-400">Order Ref:</span>
                  <span className="font-mono font-medium text-gray-800 dark:text-gray-200">
                    {workflowResult.complaint_analysis.order_number || 'None'}
                  </span>
                </div>
                <div>
                  <span className="block text-gray-400">Analysis Engine:</span>
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {workflowResult.complaint_analysis.analysis_method}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Section B: Order Investigation */}
        {workflowResult.order_investigation && (
          <Card variant="default">
            <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                  <CardTitle className="text-base">Order Investigation</CardTitle>
                </div>
                <Badge
                  variant={workflowResult.order_investigation.order_exists ? 'success' : 'error'}
                  size="sm"
                >
                  {workflowResult.order_investigation.order_exists ? 'Order Found' : 'Order Not Found'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-3 text-xs">
              {workflowResult.order_investigation.order_details ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {workflowResult.order_investigation.order_details.product_name}
                      </span>
                      <span className="text-[11px] font-mono text-gray-500 block">
                        {workflowResult.order_investigation.order_details.order_number}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-sm text-gray-900 dark:text-white font-mono">
                        {workflowResult.order_investigation.order_details.total_amount_formatted ||
                          formatPaiseToINR(workflowResult.order_investigation.order_details.total_amount)}
                      </span>
                      <span className="text-[10px] text-gray-400 block uppercase">
                        {workflowResult.order_investigation.order_details.category}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] p-2 rounded bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                    <div>
                      <span className="text-gray-400 block">Delivery Status:</span>
                      <span className="font-semibold capitalize text-gray-800 dark:text-gray-200">
                        {workflowResult.order_investigation.order_details.delivery_status}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400 block">Refund Record:</span>
                      <span className="font-semibold capitalize text-gray-800 dark:text-gray-200">
                        {workflowResult.order_investigation.refund_status}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 italic text-xs">
                  {workflowResult.order_investigation.limitations || 'No order details available in database.'}
                </p>
              )}

              {workflowResult.order_investigation.delivery_summary && (
                <p className="text-gray-700 dark:text-gray-300 text-xs">
                  {workflowResult.order_investigation.delivery_summary}
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* 6. Section C: Policy Evidence */}
      {workflowResult.policy_evidence && (
        <Card variant="default">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                <CardTitle className="text-base">Policy Evidence & Citations</CardTitle>
              </div>
              <Badge variant="neutral" size="sm">
                RAG: {workflowResult.policy_evidence.retrieval_method}
              </Badge>
            </div>
            <CardDescription>
              {workflowResult.policy_evidence.explanation}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 pt-3 text-xs">
            {workflowResult.policy_evidence.passages &&
            workflowResult.policy_evidence.passages.length > 0 ? (
              <div className="space-y-2">
                {workflowResult.policy_evidence.passages.map((p, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-1"
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-bold text-brand-forest dark:text-brand-sage font-mono">
                        {p.document_name}
                      </span>
                      {p.policy_id && (
                        <span className="font-mono text-gray-400">{p.policy_id}</span>
                      )}
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 leading-relaxed text-xs italic">
                      "{p.passage}"
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic text-xs">
                No policy passages retrieved for this category.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* 7. Section G: Support Ticket Creation */}
      <Card variant="default">
        <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
          <div className="flex items-center gap-2">
            <Ticket className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
            <CardTitle className="text-base">Support Ticket Operations</CardTitle>
          </div>
          <CardDescription>
            Generate an official customer support ticket linked to this case record
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pt-3 text-xs">
          {createdTicket ? (
            <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5 text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  Support Ticket Successfully Linked
                </span>
                <Badge variant="success" size="sm">
                  {createdTicket.status.toUpperCase()}
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs pt-1">
                <div>
                  <span className="text-[10px] uppercase text-gray-500 block">Ticket Number</span>
                  <span className="font-mono font-bold text-gray-900 dark:text-white">
                    {createdTicket.ticket_number}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-gray-500 block">Category</span>
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {createdTicket.category}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-gray-500 block">Case ID</span>
                  <span className="font-mono text-gray-800 dark:text-gray-200">
                    #{createdTicket.case_id}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {ticketError && (
                <div
                  className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2"
                  role="alert"
                >
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{ticketError}</span>
                </div>
              )}

              {workflowResult.case_id ? (
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <div className="flex-1">
                    <label
                      htmlFor="ticket_category"
                      className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1"
                    >
                      Ticket Category
                    </label>
                    <select
                      id="ticket_category"
                      value={ticketCategory}
                      onChange={(e) => setTicketCategory(e.target.value)}
                      disabled={isCreatingTicket}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage"
                    >
                      <option value="damaged_product">Damaged Product / Return</option>
                      <option value="delayed_delivery">Delayed Delivery / Logistics</option>
                      <option value="refund_request">Refund Inquiry</option>
                      <option value="general_inquiry">General Inquiry</option>
                    </select>
                  </div>

                  <div className="sm:self-end">
                    <Button
                      type="button"
                      variant="primary"
                      size="md"
                      onClick={handleCreateTicket}
                      isLoading={isCreatingTicket}
                      disabled={isCreatingTicket}
                      className="w-full sm:w-auto font-semibold text-xs"
                    >
                      <Ticket className="w-3.5 h-3.5 mr-1.5" />
                      Generate Ticket for Case #{workflowResult.case_id}
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 italic text-xs">
                  This workflow execution did not persist a database case record. Ticket creation requires an associated case ID.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 8. Section H: Execution Audit Trail Notice & Recorded Events */}
      <Card variant="default">
        <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
            <CardTitle className="text-base">Workflow Execution Audit Trail</CardTitle>
          </div>
          <CardDescription>
            Chronological audit events recorded during this autonomous orchestration run
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pt-3 text-xs">
          {workflowResult.events_recorded && workflowResult.events_recorded.length > 0 ? (
            <div className="space-y-2">
              {workflowResult.events_recorded.map((ev, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-xs flex items-start gap-2"
                >
                  <span className="font-mono text-[10px] text-gray-400 pt-0.5 shrink-0">
                    #{idx + 1}
                  </span>
                  <div className="space-y-0.5 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-brand-forest dark:text-brand-sage">
                        {String(ev.event_type || 'workflow_event')}
                      </span>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300">
                      {String(ev.message || JSON.stringify(ev))}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 italic text-xs">
              No audit events recorded for this run.
            </p>
          )}

          <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-[11px] text-gray-500 dark:text-gray-400">
            <strong>API Capability Note:</strong> The ResolveAI backend provides a write-only audit endpoint (<code>POST /api/v1/cases/{'{case_id}'}/events</code>). No historical event query endpoint (<code>GET /cases/{'{case_id}'}/events</code>) is implemented in the backend. Only events produced during this workflow invocation are shown above.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
