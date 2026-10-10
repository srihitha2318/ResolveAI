import React, { useState } from 'react'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Card } from '../common/Card'
import {
  Send,
  AlertCircle,
  CheckCircle2,
  Clock,
  HelpCircle,
  FileText,
  ArrowRight,
  Info,
} from 'lucide-react'
import { resolveComplaint, verifyCustomerAccess } from '../../services/api'
import type { WorkflowResolveResponse } from '../../types/workflow'

interface CustomerComplaintFormProps {
  onCaseCreated?: (caseNumber: string) => void
  onOpenClarification?: (threadId: string) => void
}

export const CustomerComplaintForm: React.FC<CustomerComplaintFormProps> = ({
  onCaseCreated,
  onOpenClarification,
}) => {
  const [email, setEmail] = useState('')
  const [orderNumber, setOrderNumber] = useState('')
  const [category, setCategory] = useState<'electronics' | 'fashion' | 'home_appliances' | 'general_merchandise' | ''>('')
  const [complaintText, setComplaintText] = useState('')

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<WorkflowResolveResponse | null>(null)

  const validate = (): boolean => {
    const errs: Record<string, string> = {}
    const trimmedEmail = email.trim()
    const trimmedText = complaintText.trim()

    if (!trimmedEmail) {
      errs.email = 'Registered customer email is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      errs.email = 'Please provide a valid email format (e.g. name@example.com).'
    }

    if (!trimmedText) {
      errs.complaintText = 'Complaint description is required.'
    } else if (trimmedText.length < 15) {
      errs.complaintText = 'Please provide at least 15 characters describing your issue.'
    }

    if (orderNumber.trim()) {
      const trimmedOrder = orderNumber.trim()
      if (trimmedOrder.includes('/') || trimmedOrder.includes('\\') || trimmedOrder.includes('..')) {
        errs.orderNumber = 'Invalid characters detected in order number.'
      }
    }

    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate() || isSubmitting) return

    setIsSubmitting(true)
    setSubmitError(null)
    setWorkflowResult(null)

    try {
      // 1. Submit to real LangGraph complaint resolution workflow
      const result = await resolveComplaint({
        complaint_text: complaintText.trim(),
        order_number: orderNumber.trim() || undefined,
        category: category || undefined,
      })

      setWorkflowResult(result)

      // Automatically attempt customer verification in background to save session token for tracking
      if (email.trim()) {
        try {
          await verifyCustomerAccess({
            email: email.trim(),
            order_number: orderNumber.trim() || undefined,
            case_number: result.case_number || undefined,
          })
        } catch {
          // Non-blocking: customer can still track manually
        }
      }

      if (result.case_number && onCaseCreated) {
        onCaseCreated(result.case_number)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit complaint. Please try again.'
      setSubmitError(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setWorkflowResult(null)
    setSubmitError(null)
    setComplaintText('')
    setOrderNumber('')
    setCategory('')
  }

  return (
    <div className="space-y-8">
      {/* Form Card */}
      {!workflowResult ? (
        <Card className="p-6 md:p-8 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card">
          <div className="space-y-2 mb-6">
            <h2 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-forest dark:text-brand-sage" />
              File a Customer Complaint
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Fill in your registered order information. Our AI agents will verify order delivery status and store policies.
            </p>
          </div>

          {submitError && (
            <div
              id="customer-complaint-error"
              className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 text-sm flex items-start gap-3 mb-6"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold">Unable to process complaint</p>
                <p>{submitError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            {/* Customer Email */}
            <div>
              <label
                htmlFor="complaint-customer-email"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Registered Email Address <span className="text-red-500">*</span>
              </label>
              <input
                id="complaint-customer-email"
                type="email"
                placeholder="e.g. alice.chen@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (errors.email) setErrors((prev) => ({ ...prev, email: '' }))
                }}
                disabled={isSubmitting}
                className={`w-full px-4 py-2.5 rounded-lg border text-sm transition-colors bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage ${
                  errors.email
                    ? 'border-red-500 dark:border-red-500'
                    : 'border-gray-300 dark:border-dark-border'
                }`}
              />
              {errors.email && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.email}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Order Number */}
              <div>
                <label
                  htmlFor="complaint-order-number"
                  className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
                >
                  Order Number (Optional)
                </label>
                <input
                  id="complaint-order-number"
                  type="text"
                  placeholder="e.g. ORD-2026-001"
                  value={orderNumber}
                  onChange={(e) => {
                    setOrderNumber(e.target.value)
                    if (errors.orderNumber) setErrors((prev) => ({ ...prev, orderNumber: '' }))
                  }}
                  disabled={isSubmitting}
                  className={`w-full px-4 py-2.5 rounded-lg border text-sm transition-colors bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage ${
                    errors.orderNumber
                      ? 'border-red-500 dark:border-red-500'
                      : 'border-gray-300 dark:border-dark-border'
                  }`}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Leaving blank prompts clarification for missing order.
                </p>
                {errors.orderNumber && (
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {errors.orderNumber}
                  </p>
                )}
              </div>

              {/* Product Category Hint */}
              <div>
                <label
                  htmlFor="complaint-category-select"
                  className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
                >
                  Product Category (Optional)
                </label>
                <select
                  id="complaint-category-select"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as any)}
                  disabled={isSubmitting}
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-dark-border text-sm transition-colors bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage"
                >
                  <option value="">Auto-detect from complaint</option>
                  <option value="electronics">Electronics (Computers, Audio, Monitors)</option>
                  <option value="fashion">Fashion & Apparel</option>
                  <option value="home_appliances">Home & Kitchen Appliances</option>
                  <option value="general_merchandise">General Merchandise</option>
                </select>
              </div>
            </div>

            {/* Complaint Text */}
            <div>
              <label
                htmlFor="complaint-description"
                className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Describe Your Issue in Detail <span className="text-red-500">*</span>
              </label>
              <textarea
                id="complaint-description"
                rows={5}
                placeholder="Please describe what happened, package condition, delivery delays, or defects..."
                value={complaintText}
                onChange={(e) => {
                  setComplaintText(e.target.value)
                  if (errors.complaintText) setErrors((prev) => ({ ...prev, complaintText: '' }))
                }}
                disabled={isSubmitting}
                className={`w-full px-4 py-3 rounded-lg border text-sm transition-colors bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage ${
                  errors.complaintText
                    ? 'border-red-500 dark:border-red-500'
                    : 'border-gray-300 dark:border-dark-border'
                }`}
              />
              <div className="flex justify-between items-center text-xs mt-1 text-gray-500 dark:text-gray-400">
                <span>Minimum 15 characters</span>
                <span>{complaintText.length} characters</span>
              </div>
              {errors.complaintText && (
                <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {errors.complaintText}
                </p>
              )}
            </div>

            {/* Demo Helper Prompt Buttons */}
            <div className="p-3.5 rounded-lg bg-gray-50 dark:bg-dark-bg/60 border border-gray-200 dark:border-dark-border/60 text-xs space-y-2">
              <span className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                Quick Demo Templates:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEmail('alice.chen@example.com')
                    setOrderNumber('ORD-2026-001')
                    setComplaintText('The ergonomic office chair delivered yesterday has a defective hydraulic cylinder that does not hold height.')
                  }}
                  className="px-2.5 py-1 rounded bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border hover:border-brand-sage text-gray-700 dark:text-gray-300"
                >
                  Standard Defect (ORD-2026-001)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmail('bob.martinez@example.com')
                    setOrderNumber('ORD-2026-003')
                    setComplaintText('The Ultra-HD monitor was severely damaged during transit, screen glass is shattered on arrival.')
                  }}
                  className="px-2.5 py-1 rounded bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border hover:border-brand-sage text-gray-700 dark:text-gray-300"
                >
                  High-Value Escalation (ORD-2026-003)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmail('alice.chen@example.com')
                    setOrderNumber('')
                    setComplaintText('I never received my package that was supposed to arrive last Friday, please help track it.')
                  }}
                  className="px-2.5 py-1 rounded bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border hover:border-brand-sage text-gray-700 dark:text-gray-300"
                >
                  Missing Order Clarification
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex justify-end pt-2">
              <Button
                id="complaint-submit-btn"
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isSubmitting}
                className="w-full sm:w-auto font-semibold"
                leftIcon={<Send className="w-4 h-4" />}
              >
                {isSubmitting ? 'Analyzing Complaint...' : 'Submit Complaint'}
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        /* Response Status View */
        <Card className="p-6 md:p-8 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card space-y-6">
          {/* Header depending on state */}
          {workflowResult.status === 'completed' && (
            <div className="flex items-start gap-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold">Complaint Processed & Verified</h3>
                  <Badge variant="success" size="sm">Completed</Badge>
                </div>
                <p className="text-sm text-emerald-800 dark:text-emerald-200">
                  Your complaint was analyzed and resolved according to policy. An internal support ticket has been recorded.
                </p>
              </div>
            </div>
          )}

          {workflowResult.status === 'needs_review' && (
            <div className="flex items-start gap-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-100">
              <Clock className="w-6 h-6 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold">Pending Supervisor Review</h3>
                  <Badge variant="warning" size="sm">Awaiting Review</Badge>
                </div>
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  This case requires supervisor authorization due to order value or policy thresholds. A supervisor has been alerted under active SLA monitoring.
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-300 font-medium pt-1">
                  Notice: No payment or refund has been executed yet. The proposed resolution is awaiting review.
                </p>
              </div>
            </div>
          )}

          {workflowResult.status === 'needs_information' && (
            <div className="flex items-start gap-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-100">
              <HelpCircle className="w-6 h-6 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold">Additional Information Required</h3>
                  <Badge variant="pending" size="sm">Awaiting Information</Badge>
                </div>
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  We need additional information (such as your specific order number or item photos) to continue processing this complaint.
                </p>
                {workflowResult.missing_information && workflowResult.missing_information.length > 0 && (
                  <div className="text-xs bg-white/60 dark:bg-dark-card/60 p-2.5 rounded-lg border border-blue-200 dark:border-blue-900">
                    <span className="font-semibold">Missing fields: </span>
                    {workflowResult.missing_information.join(', ')}
                  </div>
                )}
                {workflowResult.thread_id && onOpenClarification && (
                  <div className="pt-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => onOpenClarification(workflowResult.thread_id!)}
                      leftIcon={<ArrowRight className="w-4 h-4" />}
                    >
                      Provide Missing Information Now
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Case Reference Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
            <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Case Number</p>
              <p className="text-base font-bold text-gray-900 dark:text-white mt-0.5">
                {workflowResult.case_number || 'N/A'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Workflow Run ID</p>
              <p className="text-xs font-mono font-medium text-gray-800 dark:text-gray-300 mt-1 truncate">
                {workflowResult.workflow_id}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Current Stage</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-white mt-0.5 capitalize">
                {workflowResult.current_stage || 'Triage'}
              </p>
            </div>
          </div>

          {/* Recommended Resolution (if completed) */}
          {workflowResult.recommended_resolution && (
            <div className="p-4 rounded-xl bg-brand-softGray dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-2">
              <h4 className="text-sm font-bold text-gray-900 dark:text-white">
                {workflowResult.recommended_resolution.title || 'Proposed Resolution Action:'}
              </h4>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {workflowResult.recommended_resolution.reasoning || 'Processed in accordance with merchant return window.'}
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Badge variant="neutral" size="sm">
                  Action: {workflowResult.recommended_resolution.action_required}
                </Badge>
                {workflowResult.recommended_resolution.recommendation_type && (
                  <Badge variant="neutral" size="sm">
                    Type: {workflowResult.recommended_resolution.recommendation_type}
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Next Steps Guidance */}
          <div className="p-4 rounded-xl bg-gray-50 dark:bg-dark-bg/60 border border-gray-200 dark:border-dark-border space-y-2 text-xs text-gray-600 dark:text-gray-400">
            <h4 className="font-bold text-gray-900 dark:text-white">Next Steps for Customer:</h4>
            <ul className="list-disc pl-4 space-y-1">
              <li>Save your case number ({workflowResult.case_number}) for future inquiries.</li>
              <li>You can track progress anytime from the "Track Existing Case" tab using your registered email.</li>
              {workflowResult.status === 'needs_review' && (
                <li>Our senior supervisor team reviews cases within standard SLA guidelines.</li>
              )}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex justify-between items-center pt-4 border-t border-gray-200 dark:border-dark-border">
            <Button variant="outline" size="sm" onClick={handleReset}>
              Submit Another Complaint
            </Button>
            {workflowResult.case_number && onCaseCreated && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onCaseCreated(workflowResult.case_number!)}
                leftIcon={<ArrowRight className="w-4 h-4" />}
              >
                Track Case Now
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
