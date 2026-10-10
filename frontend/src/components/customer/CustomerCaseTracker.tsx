import React, { useState, useEffect } from 'react'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Card } from '../common/Card'
import {
  Search,
  Lock,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  LogOut,
  RefreshCw,
} from 'lucide-react'
import {
  verifyCustomerAccess,
  getCustomerCases,
  getCustomerCaseDetail,
  getCustomerToken,
  clearCustomerToken,
} from '../../services/api'
import type { CustomerCaseSummary, CustomerCaseDetail } from '../../types/customer'
import { CustomerClarificationModal } from './CustomerClarificationModal'

interface CustomerCaseTrackerProps {
  initialCaseId?: string
}

export const CustomerCaseTracker: React.FC<CustomerCaseTrackerProps> = ({ initialCaseId }) => {
  // Verification input states
  const [email, setEmail] = useState('')
  const [orderOrCaseNumber, setOrderOrCaseNumber] = useState(initialCaseId || '')
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState<string | null>(null)

  // Authenticated customer state
  const [customerEmail, setCustomerEmail] = useState<string | null>(null)
  const [customerName, setCustomerName] = useState<string | null>(null)
  const [cases, setCases] = useState<CustomerCaseSummary[]>([])
  const [selectedCaseNumber, setSelectedCaseNumber] = useState<string | null>(initialCaseId || null)
  const [activeCaseDetail, setActiveCaseDetail] = useState<CustomerCaseDetail | null>(null)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  // Clarification modal
  const [clarificationThreadId, setClarificationThreadId] = useState<string | null>(null)

  // Check if customer already has a valid session token in sessionStorage
  useEffect(() => {
    const existingToken = getCustomerToken()
    if (!existingToken) return

    let isSubscribed = true
    getCustomerCases()
      .then((fetchedCases) => {
        if (!isSubscribed) return
        setCases(fetchedCases)
        setCustomerEmail('Registered Customer')
        if (initialCaseId) {
          setSelectedCaseNumber(initialCaseId)
        } else if (fetchedCases.length > 0) {
          setSelectedCaseNumber(fetchedCases[0].case_number)
        }
      })
      .catch(() => {
        if (isSubscribed) clearCustomerToken()
      })

    return () => {
      isSubscribed = false
    }
  }, [initialCaseId])

  // When selected case number changes, fetch its sanitized details
  useEffect(() => {
    if (!selectedCaseNumber) return

    let isSubscribed = true
    getCustomerCaseDetail(selectedCaseNumber)
      .then((detail) => {
        if (isSubscribed) {
          setActiveCaseDetail(detail)
          setIsLoadingDetail(false)
        }
      })
      .catch((err) => {
        if (isSubscribed) {
          const msg = err instanceof Error ? err.message : 'Unable to load case details.'
          setDetailError(msg)
          setIsLoadingDetail(false)
        }
      })

    return () => {
      isSubscribed = false
    }
  }, [selectedCaseNumber])

  const handleVerifyAccess = async (e: React.FormEvent) => {
    e.preventDefault()
    setVerificationError(null)

    const cleanEmail = email.trim()
    const cleanNum = orderOrCaseNumber.trim()

    if (!cleanEmail) {
      setVerificationError('Please enter your registered email address.')
      return
    }

    setIsVerifying(true)

    try {
      const isCase = cleanNum.toUpperCase().startsWith('CASE-')
      const resp = await verifyCustomerAccess({
        email: cleanEmail,
        order_number: isCase ? undefined : cleanNum || undefined,
        case_number: isCase ? cleanNum : undefined,
      })

      setCustomerEmail(resp.customer_email)
      setCustomerName(resp.customer_name)
      setCases(resp.cases)

      if (cleanNum && isCase) {
        setSelectedCaseNumber(cleanNum)
      } else if (resp.cases.length > 0) {
        setSelectedCaseNumber(resp.cases[0].case_number)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed. Please verify your credentials.'
      setVerificationError(msg)
    } finally {
      setIsVerifying(false)
    }
  }

  const handleSignOutCustomer = () => {
    clearCustomerToken()
    setCustomerEmail(null)
    setCustomerName(null)
    setCases([])
    setSelectedCaseNumber(null)
    setActiveCaseDetail(null)
  }

  const refreshCaseList = async () => {
    if (!customerEmail) return
    try {
      const fetched = await getCustomerCases()
      setCases(fetched)
      if (selectedCaseNumber) {
        const detail = await getCustomerCaseDetail(selectedCaseNumber)
        setActiveCaseDetail(detail)
      }
    } catch {
      // Silently catch
    }
  }

  return (
    <div className="space-y-6">
      {/* If not authenticated as customer, show secure verification card */}
      {!customerEmail ? (
        <Card className="max-w-xl mx-auto p-6 md:p-8 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card">
          <div className="space-y-2 mb-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-brand-forest/10 dark:bg-brand-forest/30 text-brand-forest dark:text-brand-sage flex items-center justify-center mx-auto mb-3">
              <Lock className="w-6 h-6" />
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">
              Secure Case Tracking
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              To protect customer privacy, please verify ownership with your registered email and order or case number.
            </p>
          </div>

          {verificationError && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 text-sm flex items-start gap-3 mb-6">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500 mt-0.5" />
              <div>
                <p className="font-semibold">Verification Failed</p>
                <p className="text-xs mt-0.5">{verificationError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleVerifyAccess} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="track-email-input"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Registered Email Address <span className="text-red-500">*</span>
              </label>
              <input
                id="track-email-input"
                type="email"
                placeholder="e.g. alice.chen@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isVerifying}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-dark-border text-sm bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest"
              />
            </div>

            <div>
              <label
                htmlFor="track-order-case-input"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Order or Case Number (Optional)
              </label>
              <input
                id="track-order-case-input"
                type="text"
                placeholder="e.g. ORD-2026-001 or CASE-2026-1001"
                value={orderOrCaseNumber}
                onChange={(e) => setOrderOrCaseNumber(e.target.value)}
                disabled={isVerifying}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-dark-border text-sm bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Verifies that you own this specific record.
              </p>
            </div>

            {/* Quick Demo Credentials */}
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-xs space-y-1.5">
              <span className="font-semibold text-gray-700 dark:text-gray-300">Demo Accounts:</span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEmail('alice.chen@example.com')
                    setOrderOrCaseNumber('ORD-2026-001')
                  }}
                  className="px-2 py-1 rounded bg-white dark:bg-dark-card border text-gray-700 dark:text-gray-300 hover:border-brand-sage"
                >
                  Alice Chen (ORD-2026-001)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmail('bob.martinez@example.com')
                    setOrderOrCaseNumber('CASE-2026-1002')
                  }}
                  className="px-2 py-1 rounded bg-white dark:bg-dark-card border text-gray-700 dark:text-gray-300 hover:border-brand-sage"
                >
                  Bob Martinez (CASE-2026-1002)
                </button>
              </div>
            </div>

            <Button
              id="verify-customer-access-btn"
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isVerifying}
              className="w-full font-semibold mt-2"
              leftIcon={<Search className="w-4 h-4" />}
            >
              {isVerifying ? 'Verifying Ownership...' : 'View My Support Cases'}
            </Button>
          </form>
        </Card>
      ) : (
        /* Authenticated Customer Case Portal */
        <div className="space-y-6">
          {/* Customer Header Session Strip */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-brand-forest text-white font-bold flex items-center justify-center text-sm">
                {(customerName || customerEmail).charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-bold text-gray-900 dark:text-white">
                  {customerName || 'Verified Customer'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{customerEmail}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={refreshCaseList}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSignOutCustomer}
                className="text-red-600 dark:text-red-400 hover:bg-red-50"
                leftIcon={<LogOut className="w-3.5 h-3.5" />}
              >
                Sign Out
              </Button>
            </div>
          </div>

          {/* Cases Grid / Detail Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Case List Sidebar */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                  Your Support Cases ({cases.length})
                </h3>
              </div>

              {cases.length === 0 ? (
                <Card className="p-6 text-center text-xs text-gray-500 dark:text-gray-400">
                  No cases found for this account.
                </Card>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {cases.map((c) => (
                    <button
                      key={c.case_number}
                      type="button"
                      onClick={() => setSelectedCaseNumber(c.case_number)}
                      className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                        selectedCaseNumber === c.case_number
                          ? 'bg-brand-forest/5 dark:bg-brand-forest/20 border-brand-forest dark:border-brand-sage shadow-sm'
                          : 'bg-white dark:bg-dark-card border-gray-200 dark:border-dark-border hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-bold text-xs text-gray-900 dark:text-white">
                          {c.case_number}
                        </span>
                        <Badge
                          variant={
                            c.status === 'resolved'
                              ? 'success'
                              : c.status === 'in_progress'
                              ? 'pending'
                              : c.status === 'escalated'
                              ? 'warning'
                              : 'neutral'
                          }
                          size="sm"
                        >
                          {c.status}
                        </Badge>
                      </div>

                      <p className="text-xs font-medium text-gray-800 dark:text-gray-200 line-clamp-1 mb-1">
                        {c.subject}
                      </p>

                      <div className="flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
                        <span>{c.order_number || 'No order'}</span>
                        {c.clarification_needed && (
                          <span className="text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> Action Needed
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Case Detail View */}
            <div className="lg:col-span-2 space-y-6">
              {isLoadingDetail ? (
                <Card className="p-12 text-center text-sm text-gray-500 dark:text-gray-400">
                  <div className="w-8 h-8 border-2 border-brand-forest border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  Loading case details...
                </Card>
              ) : detailError ? (
                <Card className="p-6 bg-red-50 dark:bg-red-950/20 border-red-200 text-red-700 text-sm">
                  {detailError}
                </Card>
              ) : activeCaseDetail ? (
                <Card className="p-6 md:p-8 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card space-y-6">
                  {/* Status Banner */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-gray-200 dark:border-dark-border">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                          {activeCaseDetail.case_number}
                        </h3>
                        <Badge
                          variant={
                            activeCaseDetail.status === 'resolved'
                              ? 'success'
                              : activeCaseDetail.status === 'escalated'
                              ? 'warning'
                              : 'pending'
                          }
                          size="sm"
                        >
                          {activeCaseDetail.status.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Filed on {new Date(activeCaseDetail.created_at).toLocaleString()}
                      </p>
                    </div>

                    {activeCaseDetail.ticket_number && (
                      <div className="text-right">
                        <span className="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
                          Support Ticket
                        </span>
                        <p className="text-xs font-mono font-bold text-brand-forest dark:text-brand-sage">
                          {activeCaseDetail.ticket_number}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Clarification Action Callout (if awaiting customer input) */}
                  {activeCaseDetail.clarification_needed && activeCaseDetail.thread_id && (
                    <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-100 flex flex-wrap items-center justify-between gap-4">
                      <div className="space-y-1 max-w-lg">
                        <div className="flex items-center gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                          <p className="text-sm font-bold">Action Required from You</p>
                        </div>
                        <p className="text-xs text-amber-800 dark:text-amber-200">
                          {activeCaseDetail.clarification_prompt ||
                            'Our support agent or AI system needs additional facts to proceed with this resolution.'}
                        </p>
                      </div>
                      <Button
                        variant="primary"
                        size="sm"
                        className="bg-amber-600 hover:bg-amber-700 text-white"
                        onClick={() => setClarificationThreadId(activeCaseDetail.thread_id!)}
                        leftIcon={<ArrowRight className="w-3.5 h-3.5" />}
                      >
                        Provide Information
                      </Button>
                    </div>
                  )}

                  {/* Order & Product Reference Card */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-1">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Order Number
                      </span>
                      <p className="text-sm font-bold text-gray-900 dark:text-white">
                        {activeCaseDetail.order_number || 'N/A'}
                      </p>
                      {activeCaseDetail.product_name && (
                        <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-1">
                          Product: {activeCaseDetail.product_name}
                        </p>
                      )}
                    </div>

                    <div className="p-4 rounded-xl bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-1">
                      <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                        Fulfillment Status
                      </span>
                      <p className="text-sm font-bold text-gray-900 dark:text-white capitalize">
                        {activeCaseDetail.order_status || 'Delivered'}
                      </p>
                      {activeCaseDetail.delivery_status && (
                        <p className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                          Delivery: {activeCaseDetail.delivery_status}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Complaint Description */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                      Submitted Complaint Description
                    </h4>
                    <div className="p-4 rounded-xl bg-brand-softGray dark:bg-dark-bg text-sm text-gray-800 dark:text-gray-200 leading-relaxed border border-gray-200/60 dark:border-dark-border">
                      {activeCaseDetail.complaint_text}
                    </div>
                  </div>

                  {/* Resolution Summary (if resolved) */}
                  {activeCaseDetail.resolution_summary && (
                    <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100 space-y-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <h4 className="text-sm font-bold">Official Resolution Summary</h4>
                      </div>
                      <p className="text-xs text-emerald-800 dark:text-emerald-200 leading-relaxed">
                        {activeCaseDetail.resolution_summary}
                      </p>
                    </div>
                  )}

                  {/* Resolution Safety Guarantee Notice */}
                  <div className="p-4 rounded-xl bg-gray-50 dark:bg-dark-bg/60 border border-gray-200 dark:border-dark-border text-xs text-gray-500 dark:text-gray-400 space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-gray-700 dark:text-gray-300">
                      <ShieldCheck className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                      <span>Security & Privacy Boundary</span>
                    </div>
                    <p>
                      This customer view shows only authorized case details and policy findings. Internal supervisor notes,
                      staff reviewer credentials, and internal audit traces are securely withheld.
                    </p>
                  </div>
                </Card>
              ) : (
                <Card className="p-12 text-center text-sm text-gray-500 dark:text-gray-400">
                  Select a support case from the list on the left to view tracking status.
                </Card>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Clarification Modal */}
      {clarificationThreadId && activeCaseDetail && (
        <CustomerClarificationModal
          isOpen={Boolean(clarificationThreadId)}
          onClose={() => setClarificationThreadId(null)}
          threadId={clarificationThreadId}
          caseNumber={activeCaseDetail.case_number}
          missingFields={activeCaseDetail.missing_fields}
          clarificationPrompt={activeCaseDetail.clarification_prompt || undefined}
          customerEmail={customerEmail || undefined}
          onClarificationSubmitted={() => {
            refreshCaseList()
            setClarificationThreadId(null)
          }}
        />
      )}
    </div>
  )
}
