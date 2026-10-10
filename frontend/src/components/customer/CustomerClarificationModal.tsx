import React, { useState } from 'react'
import { Modal } from '../common/Modal'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { AlertCircle, CheckCircle2, Send, HelpCircle } from 'lucide-react'
import { submitCustomerClarification } from '../../services/api'
import type { ProvideInformationResponse } from '../../types/workflow'

interface CustomerClarificationModalProps {
  isOpen: boolean
  onClose: () => void
  threadId: string
  caseNumber?: string
  missingFields?: string[]
  clarificationPrompt?: string
  customerEmail?: string
  onClarificationSubmitted?: () => void
}

export const CustomerClarificationModal: React.FC<CustomerClarificationModalProps> = ({
  isOpen,
  onClose,
  threadId,
  caseNumber,
  missingFields = [],
  clarificationPrompt,
  customerEmail,
  onClarificationSubmitted,
}) => {
  const [orderNumber, setOrderNumber] = useState('')
  const [details, setDetails] = useState('')
  const [emailInput, setEmailInput] = useState(customerEmail || '')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ProvideInformationResponse | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const trimmedOrder = orderNumber.trim()
    const trimmedDetails = details.trim()
    const trimmedEmail = emailInput.trim()

    if (!trimmedOrder && !trimmedDetails) {
      setError('Please provide at least one piece of clarification (order number or additional details).')
      return
    }

    if (trimmedOrder && (trimmedOrder.includes('/') || trimmedOrder.includes('\\') || trimmedOrder.includes('..'))) {
      setError('Order number cannot contain path traversal patterns.')
      return
    }

    setIsSubmitting(true)

    try {
      const resp = await submitCustomerClarification(threadId, {
        order_number: trimmedOrder || undefined,
        additional_details: trimmedDetails || undefined,
        customer_email: trimmedEmail || undefined,
      })

      setResult(resp)
      if (onClarificationSubmitted) {
        onClarificationSubmitted()
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit clarification. Please try again.'
      setError(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleModalClose = () => {
    setResult(null)
    setError(null)
    setOrderNumber('')
    setDetails('')
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleModalClose}
      title="Provide Missing Customer Information"
    >
      <div className="space-y-6">
        {caseNumber && (
          <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-xs">
            <span className="text-gray-500 dark:text-gray-400">Associated Case:</span>
            <span className="font-bold text-gray-900 dark:text-white">{caseNumber}</span>
          </div>
        )}

        {clarificationPrompt && (
          <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 text-blue-900 dark:text-blue-100 text-sm space-y-1">
            <div className="flex items-center gap-2 font-semibold">
              <HelpCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Requested Clarification:</span>
            </div>
            <p className="text-xs text-blue-800 dark:text-blue-200">{clarificationPrompt}</p>
          </div>
        )}

        {missingFields.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
            <span className="font-semibold">Required fields:</span>
            {missingFields.map((field) => (
              <Badge key={field} variant="warning" size="sm">
                {field}
              </Badge>
            ))}
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Customer Email */}
            <div>
              <label
                htmlFor="clarification-email"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Registered Customer Email
              </label>
              <input
                id="clarification-email"
                type="email"
                placeholder="alice.chen@example.com"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2 rounded-lg border border-gray-300 dark:border-dark-border text-sm bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest"
              />
            </div>

            {/* Order Number if needed */}
            <div>
              <label
                htmlFor="clarification-order-num"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Order Number (e.g. ORD-2026-001)
              </label>
              <input
                id="clarification-order-num"
                type="text"
                placeholder="ORD-2026-001"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2 rounded-lg border border-gray-300 dark:border-dark-border text-sm bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest"
              />
            </div>

            {/* Additional Details */}
            <div>
              <label
                htmlFor="clarification-details"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Additional Details / Item Condition Description
              </label>
              <textarea
                id="clarification-details"
                rows={4}
                placeholder="Provide the missing context, serial number, or damage details..."
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg border border-gray-300 dark:border-dark-border text-sm bg-white dark:bg-dark-bg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-forest"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" size="sm" onClick={handleModalClose}>
                Cancel
              </Button>
              <Button
                id="submit-clarification-btn"
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isSubmitting}
                leftIcon={<Send className="w-3.5 h-3.5" />}
              >
                {isSubmitting ? 'Resuming Workflow...' : 'Submit Clarification'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold text-sm">Clarification Submitted Successfully</p>
                <p className="text-xs text-emerald-800 dark:text-emerald-200">{result.message}</p>
                <div className="flex items-center gap-2 pt-1">
                  <Badge variant="success" size="sm">
                    Status: {result.workflow_status}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="primary" size="sm" onClick={handleModalClose}>
                Done
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
