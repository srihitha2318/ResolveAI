import React, { useEffect, useState } from 'react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Card, CardHeader, CardTitle, CardContent } from '../common/Card'
import { useAuth } from '../../hooks/useAuth'
import {
  getApprovalDetails,
  approveWorkflow,
  rejectWorkflow,
} from '../../services/api'
import type { ApprovalDetailResponse } from '../../types/workflow'
import { formatINR } from '../../utils/currency'
import { formatDateTime, calculateSlaRemaining } from '../../utils/dateUtils'
import { ApiError } from '../../types/api'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  User,
  ShoppingBag,
  FileText,
  HelpCircle,
} from 'lucide-react'

export interface ApprovalDetailModalProps {
  threadId: string | null
  isOpen: boolean
  onClose: () => void
  onDecisionSuccess: (message: string) => void
}

const HIGH_VALUE_THRESHOLD_PAISE = 2500000 // ₹25,000 in paise

export const ApprovalDetailModal: React.FC<ApprovalDetailModalProps> = ({
  threadId,
  isOpen,
  onClose,
  onDecisionSuccess,
}) => {
  const { user } = useAuth()
  const [detail, setDetail] = useState<ApprovalDetailResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Decision state
  const [decisionMode, setDecisionMode] = useState<'idle' | 'rejecting'>('idle')
  const [rejectReason, setRejectReason] = useState('')
  const [overrideExpired, setOverrideExpired] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !threadId) {
      return
    }

    let isMounted = true
    const fetchDetail = async () => {
      setIsLoading(true)
      setLoadError(null)
      try {
        const data = await getApprovalDetails(threadId)
        if (isMounted) {
          setDetail(data)
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg =
            err instanceof ApiError ? err.message : 'Failed to retrieve approval request details.'
          setLoadError(msg)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    fetchDetail()
    return () => {
      isMounted = false
    }
  }, [isOpen, threadId])

  if (!isOpen) return null

  // Evaluate authority and restrictions
  const orderAmountPaise = detail?.order?.total_amount ?? 0
  const isHighValue = orderAmountPaise > HIGH_VALUE_THRESHOLD_PAISE
  const isExpired = Boolean(detail?.is_expired)
  const isSenior = user?.role === 'senior_supervisor'
  const isTier2 = user?.role === 'tier2_supervisor'

  // Authority rules:
  // - tier2 cannot approve high-value claims (> ₹25k)
  // - tier2 cannot approve or reject expired claims
  // - senior can approve any claim, and can approve/reject expired claims IF overrideExpired is checked
  const tier2BlockedHighValue = isTier2 && isHighValue
  const tier2BlockedExpired = isTier2 && isExpired
  const seniorRequiresOverride = isSenior && isExpired && !overrideExpired

  const canApprove =
    !isSubmitting &&
    (isSenior || isTier2) &&
    !tier2BlockedHighValue &&
    !tier2BlockedExpired &&
    !seniorRequiresOverride

  const canReject =
    !isSubmitting &&
    (isSenior || isTier2) &&
    !tier2BlockedExpired &&
    !seniorRequiresOverride

  const slaInfo = calculateSlaRemaining(detail?.expires_at, isExpired)

  // Handlers
  const handleApprove = async () => {
    if (!threadId || !user || !canApprove) return

    if (!window.confirm('Are you sure you want to approve this complaint resolution?')) {
      return
    }

    setIsSubmitting(true)
    setActionError(null)
    try {
      const resp = await approveWorkflow(threadId, {
        reviewer_id: user.username,
        reason: 'Approved via Supervisor Command Dashboard',
        override_expired: overrideExpired,
      })
      onDecisionSuccess(`Approval decision recorded successfully for case #${resp.case_id}.`)
      onClose()
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setActionError(err.message || `Approval failed with status ${err.status}.`)
      } else {
        setActionError('Network or system error occurred while recording approval.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!threadId || !user || !canReject) return

    const trimmedReason = rejectReason.trim()
    if (!trimmedReason) {
      setActionError('A valid rejection reason is required to reject a case.')
      return
    }

    if (!window.confirm('Are you sure you want to reject this proposed resolution?')) {
      return
    }

    setIsSubmitting(true)
    setActionError(null)
    try {
      const resp = await rejectWorkflow(threadId, {
        reviewer_id: user.username,
        reason: trimmedReason,
        override_expired: overrideExpired,
      })
      onDecisionSuccess(`Rejection recorded. Case #${resp.case_id} was terminated without action.`)
      onClose()
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setActionError(err.message || `Rejection failed with status ${err.status}.`)
      } else {
        setActionError('Network or system error occurred while recording rejection.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2.5">
          <span>Supervisor Case Review</span>
          {detail?.case_number && (
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage font-bold">
              {detail.case_number}
            </span>
          )}
        </div>
      }
      description={
        detail ? `Thread: ${detail.thread_id || threadId}` : 'Loading case details...'
      }
      maxWidth="lg"
      footer={
        <div className="flex flex-col sm:flex-row items-center justify-between w-full gap-3">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Reviewer: <strong className="text-gray-800 dark:text-gray-200">{user?.username}</strong> ({user?.role})
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>

            {decisionMode === 'idle' ? (
              <>
                <Button
                  variant="danger"
                  size="sm"
                  leftIcon={<XCircle className="w-4 h-4" />}
                  onClick={() => setDecisionMode('rejecting')}
                  disabled={!canReject}
                >
                  Reject
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<CheckCircle className="w-4 h-4" />}
                  onClick={handleApprove}
                  isLoading={isSubmitting}
                  disabled={!canApprove}
                >
                  Approve Resolution
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDecisionMode('idle')}
                  disabled={isSubmitting}
                >
                  Back
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  leftIcon={<XCircle className="w-4 h-4" />}
                  onClick={handleReject}
                  isLoading={isSubmitting}
                  disabled={!canReject || !rejectReason.trim()}
                >
                  Confirm Rejection
                </Button>
              </>
            )}
          </div>
        </div>
      }
    >
      {isLoading && (
        <div className="py-12 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-brand-forest/20 border-t-brand-forest animate-spin" />
          <p className="text-xs text-gray-500 font-mono">Fetching case facts from database...</p>
        </div>
      )}

      {loadError && (
        <div className="p-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 space-y-1">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4" />
            <span>Could not load approval facts</span>
          </div>
          <p>{loadError}</p>
        </div>
      )}

      {detail && !isLoading && (
        <div className="space-y-4">
          {/* Action Error Banner */}
          {actionError && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <strong>Action Error:</strong> {actionError}
              </div>
            </div>
          )}

          {/* Expiration Alert & Override Control */}
          {isExpired && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800/80 space-y-2.5">
              <div className="flex items-start gap-2 text-amber-900 dark:text-amber-200 text-xs font-semibold">
                <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span>Target SLA Deadline Breached</span>
                  <p className="text-[11px] font-normal text-amber-800 dark:text-amber-300 mt-0.5">
                    Target deadline expired at {formatDateTime(detail.expires_at)}. Standard Tier-2 authority is suspended.
                  </p>
                </div>
              </div>

              {isTier2 && (
                <div className="p-2.5 rounded bg-amber-100/60 dark:bg-amber-900/30 text-[11px] text-amber-900 dark:text-amber-200 font-medium">
                  Tier-2 Supervisors cannot decide on expired cases. This item has been escalated to Senior Supervision.
                </div>
              )}

              {isSenior && (
                <div className="pt-2 border-t border-amber-200 dark:border-amber-800/60 flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    id="seniorOverrideToggle"
                    checked={overrideExpired}
                    onChange={(e) => setOverrideExpired(e.target.checked)}
                    className="w-4 h-4 rounded text-brand-forest focus:ring-brand-forest border-gray-300"
                  />
                  <label
                    htmlFor="seniorOverrideToggle"
                    className="text-xs font-semibold text-gray-900 dark:text-white cursor-pointer select-none"
                  >
                    Enable Senior Supervisor SLA Override (Exceptional Decision)
                  </label>
                </div>
              )}
            </div>
          )}

          {/* High Value Warning for Tier 2 */}
          {tier2BlockedHighValue && !isExpired && (
            <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong>High-Value Claim Threshold Exceeded:</strong> Order amount ({formatINR(orderAmountPaise, true)})
                exceeds the ₹25,000 Tier-2 limit. Only Senior Supervisors can approve this resolution.
              </div>
            </div>
          )}

          {/* Customer & Order Summary Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Card variant="default">
              <CardContent className="p-3.5 space-y-2 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-gray-700 dark:text-gray-300">
                  <User className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  <span>Customer Information</span>
                </div>
                <div className="space-y-0.5 text-gray-600 dark:text-gray-400">
                  <div>
                    Name: <strong className="text-gray-900 dark:text-white">{detail.customer?.name || '—'}</strong>
                  </div>
                  <div>
                    Email: <span className="font-mono">{detail.customer?.email || '—'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card variant="default">
              <CardContent className="p-3.5 space-y-2 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-gray-700 dark:text-gray-300">
                  <ShoppingBag className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  <span>Order Facts</span>
                </div>
                <div className="space-y-0.5 text-gray-600 dark:text-gray-400">
                  <div>
                    Order #: <span className="font-mono font-bold text-gray-900 dark:text-white">{detail.order?.order_number || '—'}</span>
                  </div>
                  <div>
                    Item: <span className="text-gray-800 dark:text-gray-200">{detail.order?.product_name || '—'}</span>
                  </div>
                  <div>
                    Amount:{' '}
                    <span className="font-mono font-bold text-brand-forest dark:text-brand-sage">
                      {formatINR(orderAmountPaise, true)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* AI Recommendation & Justification */}
          <Card variant="default">
            <CardHeader className="py-2.5 px-3.5 bg-gray-50/60 dark:bg-dark-bg/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-semibold text-xs text-gray-700 dark:text-gray-200">
                  <FileText className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  <span>Requested Action &amp; AI Recommendation</span>
                </div>
                <Badge variant={isHighValue ? 'warning' : 'neutral'} size="sm">
                  {detail.requested_action}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-3.5 space-y-2 text-xs">
              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300 block mb-0.5">
                  Proposed Resolution:
                </span>
                <p className="p-2.5 rounded bg-gray-50 dark:bg-dark-bg font-mono text-[11px] text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-dark-border">
                  {detail.proposed_resolution || 'No proposed resolution text provided.'}
                </p>
              </div>

              <div>
                <span className="font-semibold text-gray-700 dark:text-gray-300 block mb-0.5">
                  AI Investigation Justification:
                </span>
                <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
                  {detail.justification || '—'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Verified Policy Evidence Citations */}
          {detail.policy_evidence && (
            <Card variant="default">
              <CardHeader className="py-2.5 px-3.5">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  Policy Evidence Citations
                </CardTitle>
              </CardHeader>
              <CardContent className="p-3.5 text-xs text-gray-600 dark:text-gray-300">
                <p className="p-2.5 rounded bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/40 text-[11px] font-mono leading-relaxed text-emerald-900 dark:text-emerald-200 whitespace-pre-wrap">
                  {detail.policy_evidence}
                </p>
              </CardContent>
            </Card>
          )}

          {/* SLA Tracking Bar */}
          <div className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border flex items-center justify-between text-xs">
            <span className="text-gray-500 dark:text-gray-400">
              SLA Priority: <strong className="text-gray-800 dark:text-gray-200">{detail.sla_priority || 'Standard'}</strong>
            </span>
            <span className="text-gray-500 dark:text-gray-400">
              Time Remaining:{' '}
              <strong
                className={
                  slaInfo.isExpired
                    ? 'text-status-error font-bold'
                    : slaInfo.isUrgent
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-emerald-600 dark:text-emerald-400'
                }
              >
                {slaInfo.formatted}
              </strong>
            </span>
          </div>

          {/* Rejection Reason Form (Visible in Rejecting Mode) */}
          {decisionMode === 'rejecting' && (
            <div className="p-4 rounded-xl bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 space-y-2 animate-in fade-in">
              <label
                htmlFor="rejectReasonText"
                className="block text-xs font-bold text-rose-900 dark:text-rose-200"
              >
                Operational Rejection Reason (Mandatory)*:
              </label>
              <textarea
                id="rejectReasonText"
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Explain why this resolution is being rejected (e.g. Return window exceeded, physical damage not covered, evidence contradictory)..."
                className="w-full p-2.5 text-xs rounded-lg border border-rose-300 dark:border-rose-800 bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-status-error"
              />
              <p className="text-[10px] text-rose-700 dark:text-rose-400">
                A non-empty rejection reason is required by the backend to terminate this workflow.
              </p>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
