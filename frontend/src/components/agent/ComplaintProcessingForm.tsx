import React, { useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../common/Card'
import { Button } from '../common/Button'
import { AlertCircle, Sparkles, Send, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import type { WorkflowResolveRequest } from '../../types/workflow'

export interface ComplaintProcessingFormProps {
  onSubmit: (payload: WorkflowResolveRequest) => Promise<void>
  isLoading: boolean
}

interface SampleScenario {
  label: string
  description: string
  payload: WorkflowResolveRequest
}

const SAMPLE_SCENARIOS: SampleScenario[] = [
  {
    label: 'Damaged Electronics',
    description: 'Flagship phone received with broken display',
    payload: {
      complaint_text: 'I received my order ORD-2026-001 yesterday and the smartphone display is completely shattered out of the box. Please provide an immediate replacement or full refund.',
      order_number: 'ORD-2026-001',
      category: 'electronics',
      seller_id: 'SELLER-001',
    },
  },
  {
    label: 'Delayed Delivery',
    description: 'Delivery past expected arrival date',
    payload: {
      complaint_text: 'My order ORD-2026-004 was promised 3 days ago. The tracking has not updated and I have not received the package. Where is my shipment?',
      order_number: 'ORD-2026-004',
      category: 'fashion',
      seller_id: 'SELLER-002',
    },
  },
  {
    label: 'Missing Order Info',
    description: 'Complaint without order reference (triggers clarification loop)',
    payload: {
      complaint_text: 'My package arrived with missing items and no invoice was enclosed. Can you help me fix this?',
      order_number: '',
      category: 'general_merchandise',
      seller_id: '',
    },
  },
]

export const ComplaintProcessingForm: React.FC<ComplaintProcessingFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const [complaintText, setComplaintText] = useState('')
  const [orderNumber, setOrderNumber] = useState('')
  const [category, setCategory] = useState('')
  const [sellerId, setSellerId] = useState('')
  const [caseNumber, setCaseNumber] = useState('')
  const [caseId, setCaseId] = useState('')
  const [customerId, setCustomerId] = useState('')

  const [showAdvanced, setShowAdvanced] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleApplyScenario = (scenario: SampleScenario) => {
    setComplaintText(scenario.payload.complaint_text)
    setOrderNumber(scenario.payload.order_number || '')
    setCategory(scenario.payload.category || '')
    setSellerId(scenario.payload.seller_id || '')
    setCaseNumber('')
    setCaseId('')
    setCustomerId('')
    setValidationError(null)
  }

  const handleReset = () => {
    setComplaintText('')
    setOrderNumber('')
    setCategory('')
    setSellerId('')
    setCaseNumber('')
    setCaseId('')
    setCustomerId('')
    setValidationError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)

    const cleanComplaint = complaintText.trim()
    if (!cleanComplaint) {
      setValidationError('Please enter customer complaint text before submitting.')
      return
    }

    const payload: WorkflowResolveRequest = {
      complaint_text: cleanComplaint,
      order_number: orderNumber.trim() || undefined,
      category: category.trim() || undefined,
      seller_id: sellerId.trim() || undefined,
      case_number: caseNumber.trim() || undefined,
      case_id: caseId.trim() ? parseInt(caseId.trim(), 10) : undefined,
      customer_id: customerId.trim() ? parseInt(customerId.trim(), 10) : undefined,
    }

    await onSubmit(payload)
  }

  return (
    <Card variant="default">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
              Autonomous Complaint Intake & Resolution
            </CardTitle>
            <CardDescription>
              Submit customer issues to trigger the multi-agent orchestration workflow
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
            disabled={isLoading || (!complaintText && !orderNumber)}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 self-start sm:self-auto"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Clear Form
          </Button>
        </div>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {/* Preset Case Scenarios */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">
              Quick Test Scenarios
            </label>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_SCENARIOS.map((scenario) => (
                <button
                  key={scenario.label}
                  type="button"
                  onClick={() => handleApplyScenario(scenario)}
                  disabled={isLoading}
                  className="px-2.5 py-1 text-xs rounded-md border border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-bg hover:bg-brand-forest/10 hover:border-brand-forest dark:hover:bg-brand-sage/10 dark:hover:border-brand-sage text-gray-700 dark:text-gray-300 transition-colors text-left"
                >
                  <span className="font-semibold block">{scenario.label}</span>
                  <span className="text-[10px] text-gray-500 dark:text-gray-400">
                    {scenario.description}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Validation Error Banner */}
          {validationError && (
            <div
              className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{validationError}</span>
            </div>
          )}

          {/* Complaint Textarea */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label
                htmlFor="complaint_text"
                className="text-xs font-semibold text-gray-700 dark:text-gray-300"
              >
                Customer Complaint Description <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] text-gray-400">
                {complaintText.length} characters
              </span>
            </div>
            <textarea
              id="complaint_text"
              name="complaint_text"
              rows={4}
              value={complaintText}
              onChange={(e) => setComplaintText(e.target.value)}
              placeholder="Paste raw customer message or complaint details (e.g. My order ORD-2026-001 arrived with shattered glass...)"
              disabled={isLoading}
              className="w-full p-2.5 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all leading-relaxed"
            />
          </div>

          {/* Primary Form Fields */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="order_number"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Order Number
              </label>
              <input
                id="order_number"
                name="order_number"
                type="text"
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                placeholder="e.g. ORD-2026-001"
                disabled={isLoading}
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all"
              />
            </div>

            <div>
              <label
                htmlFor="category"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Product Category Hint
              </label>
              <select
                id="category"
                name="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={isLoading}
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all"
              >
                <option value="">Auto-Detect from Text</option>
                <option value="electronics">Electronics</option>
                <option value="fashion">Fashion</option>
                <option value="home_appliances">Home Appliances</option>
                <option value="general_merchandise">General Merchandise</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="seller_id"
                className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
              >
                Seller ID Filter
              </label>
              <select
                id="seller_id"
                name="seller_id"
                value={sellerId}
                onChange={(e) => setSellerId(e.target.value)}
                disabled={isLoading}
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all"
              >
                <option value="">Platform / Any Seller</option>
                <option value="SELLER-001">SELLER-001 (Electronics Co)</option>
                <option value="SELLER-002">SELLER-002 (Fashion Outlet)</option>
                <option value="SELLER-003">SELLER-003 (Appliances Hub)</option>
              </select>
            </div>
          </div>

          {/* Optional Advanced Identifiers Toggle */}
          <div className="pt-2 border-t border-gray-100 dark:border-dark-border/60">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-brand-forest dark:hover:text-brand-sage transition-colors"
            >
              {showAdvanced ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" />
                  Hide Advanced Identifiers
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" />
                  Show Optional Case & Customer Identifiers
                </>
              )}
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 p-3 rounded-lg bg-gray-50 dark:bg-dark-bg/60 border border-gray-200 dark:border-dark-border">
                <div>
                  <label
                    htmlFor="case_number"
                    className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1"
                  >
                    Existing Case Number
                  </label>
                  <input
                    id="case_number"
                    name="case_number"
                    type="text"
                    value={caseNumber}
                    onChange={(e) => setCaseNumber(e.target.value)}
                    placeholder="e.g. CAS-2026-0001"
                    disabled={isLoading}
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label
                    htmlFor="case_id"
                    className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1"
                  >
                    Case Database ID
                  </label>
                  <input
                    id="case_id"
                    name="case_id"
                    type="number"
                    value={caseId}
                    onChange={(e) => setCaseId(e.target.value)}
                    placeholder="e.g. 1"
                    disabled={isLoading}
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label
                    htmlFor="customer_id"
                    className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1"
                  >
                    Customer Database ID
                  </label>
                  <input
                    id="customer_id"
                    name="customer_id"
                    type="number"
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value)}
                    placeholder="e.g. 1"
                    disabled={isLoading}
                    className="w-full px-2.5 py-1.5 text-xs rounded border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-gray-50/50 dark:bg-dark-card/50 border-t border-gray-100 dark:border-dark-border/60">
          <p className="text-[11px] text-gray-500 dark:text-gray-400">
            {isLoading
              ? 'Multi-agent orchestration in progress (Complaint Analyzer → Investigator → RAG → Recommender → Verifier)...'
              : 'Orchestrates 5-agent pipeline with deterministic policy verification'}
          </p>

          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            disabled={isLoading}
            className="w-full sm:w-auto font-semibold shadow-subtle"
          >
            <Send className="w-4 h-4 mr-1.5" />
            Execute AI Resolution
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
