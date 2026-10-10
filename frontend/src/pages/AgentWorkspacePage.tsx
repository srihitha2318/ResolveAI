import React, { useState, useEffect } from 'react'
import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'
import { ComplaintProcessingForm } from '../components/agent/ComplaintProcessingForm'
import { InvestigationResultsPanel } from '../components/agent/InvestigationResultsPanel'
import { ClarificationQueueTable } from '../components/agent/ClarificationQueueTable'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import {
  FileText,
  Search,
  Sparkles,
  HelpCircle,
  AlertCircle,
  Activity,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { resolveComplaint, getOrderDetails, getCaseDetails, getSystemStatus } from '../services/api'
import type { WorkflowResolveRequest, WorkflowResolveResponse } from '../types/workflow'
import { ApiError } from '../types/api'
import { formatPaiseToINR } from '../utils/currency'

export const AgentWorkspacePage: React.FC = () => {
  const { user } = useAuth()

  const [activeTab, setActiveTab] = useState<'intake' | 'clarifications' | 'lookup'>('intake')
  const [isResolving, setIsResolving] = useState(false)
  const [workflowResult, setWorkflowResult] = useState<WorkflowResolveResponse | null>(null)
  const [resolveError, setResolveError] = useState<string | null>(null)

  // Lookup Tool States
  const [lookupQuery, setLookupQuery] = useState('')
  const [lookupType, setLookupType] = useState<'order' | 'case'>('order')
  const [isLookingUp, setIsLookingUp] = useState(false)
  const [lookupResult, setLookupResult] = useState<Record<string, unknown> | null>(null)
  const [lookupError, setLookupError] = useState<string | null>(null)

  // System Health
  const [systemOnline, setSystemOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let isMounted = true
    getSystemStatus()
      .then((res) => {
        if (isMounted) setSystemOnline(res.database === 'connected')
      })
      .catch(() => {
        if (isMounted) setSystemOnline(false)
      })
    return () => {
      isMounted = false
    }
  }, [])

  const handleResolveComplaint = async (payload: WorkflowResolveRequest) => {
    setIsResolving(true)
    setResolveError(null)
    setWorkflowResult(null)

    try {
      const response = await resolveComplaint(payload)
      setWorkflowResult(response)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setResolveError(err.message || 'Workflow execution failed. Please verify input fields.')
      } else {
        setResolveError('A network error occurred while communicating with the workflow engine.')
      }
    } finally {
      setIsResolving(false)
    }
  }

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanQuery = lookupQuery.trim()
    if (!cleanQuery) return

    setIsLookingUp(true)
    setLookupError(null)
    setLookupResult(null)

    try {
      if (lookupType === 'order') {
        const data = await getOrderDetails(cleanQuery)
        setLookupResult(data)
      } else {
        const data = await getCaseDetails(cleanQuery)
        setLookupResult(data)
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setLookupError(err.message || `No ${lookupType} found for identifier '${cleanQuery}'.`)
      } else {
        setLookupError('Failed to retrieve record.')
      }
    } finally {
      setIsLookingUp(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-brand-softgray dark:bg-dark-bg text-gray-900 dark:text-gray-100 transition-colors">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {/* Workspace Sidebar */}
        <Sidebar className="hidden lg:flex" />

        {/* Main Operational Workspace */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Top Operational Header */}
          <div className="p-4 rounded-xl bg-brand-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage flex items-center justify-center shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  Frontline Support Agent Workspace
                  <Badge variant="neutral" size="sm">
                    {user?.role || 'Staff Mode'}
                  </Badge>
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Autonomous complaint intake, order verification, policy citation, and resolution routing
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-bg text-gray-600 dark:text-gray-300">
                <Activity className="w-3.5 h-3.5 text-emerald-500" />
                <span>
                  Backend Engine:{' '}
                  <strong>{systemOnline === null ? 'Connecting...' : systemOnline ? 'Connected' : 'Offline'}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Sub-Tabs */}
          <div className="flex items-center gap-2 border-b border-gray-200 dark:border-dark-border pb-2">
            <button
              type="button"
              onClick={() => setActiveTab('intake')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === 'intake'
                  ? 'bg-brand-forest text-white shadow-subtle'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-card'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Complaint Resolution Intake
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('clarifications')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === 'clarifications'
                  ? 'bg-brand-forest text-white shadow-subtle'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-card'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5" />
              Clarifications Queue
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('lookup')}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                activeTab === 'lookup'
                  ? 'bg-brand-forest text-white shadow-subtle'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-card'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              Order & Case Inspection
            </button>
          </div>

          {/* Resolve Error Banner */}
          {resolveError && (
            <div
              className="p-3.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2 animate-in fade-in"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold">Workflow Submission Error</strong>
                <span>{resolveError}</span>
              </div>
            </div>
          )}

          {/* TAB 1: Intake & Results View */}
          {activeTab === 'intake' && (
            <div className="space-y-6">
              {!workflowResult ? (
                <ComplaintProcessingForm
                  onSubmit={handleResolveComplaint}
                  isLoading={isResolving}
                />
              ) : (
                <InvestigationResultsPanel
                  workflowResult={workflowResult}
                  onNewComplaint={() => setWorkflowResult(null)}
                />
              )}
            </div>
          )}

          {/* TAB 2: Clarifications Queue */}
          {activeTab === 'clarifications' && (
            <div className="space-y-4">
              <ClarificationQueueTable />
            </div>
          )}

          {/* TAB 3: Order & Case Lookup Tool */}
          {activeTab === 'lookup' && (
            <div className="space-y-6">
              <Card variant="default">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Search className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                    Operational Record Inspection
                  </CardTitle>
                  <CardDescription>
                    Direct database lookup for order records (GET /v1/orders/:id) or cases (GET /v1/cases/:id)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <form onSubmit={handleLookup} className="flex flex-col sm:flex-row gap-3">
                    <select
                      value={lookupType}
                      onChange={(e) => setLookupType(e.target.value as 'order' | 'case')}
                      className="px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100"
                    >
                      <option value="order">Order Number (e.g. ORD-2026-001)</option>
                      <option value="case">Case Number (e.g. CAS-2026-0001)</option>
                    </select>

                    <input
                      type="text"
                      value={lookupQuery}
                      onChange={(e) => setLookupQuery(e.target.value)}
                      placeholder={lookupType === 'order' ? 'ORD-2026-001' : 'CAS-2026-0001'}
                      className="flex-1 px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400"
                    />

                    <Button
                      type="submit"
                      variant="primary"
                      size="md"
                      isLoading={isLookingUp}
                      disabled={isLookingUp || !lookupQuery.trim()}
                      className="text-xs"
                    >
                      Search Database
                    </Button>
                  </form>

                  {lookupError && (
                    <div
                      className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2"
                      role="alert"
                    >
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{lookupError}</span>
                    </div>
                  )}

                  {lookupResult && (
                    <div className="p-4 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-gray-800 dark:text-gray-200 uppercase">
                          Record Inspection Facts
                        </span>
                        <Badge variant="success" size="sm">
                          Verified in Database
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                        {Object.entries(lookupResult).map(([key, val]) => (
                          <div key={key} className="space-y-0.5">
                            <span className="text-[10px] uppercase font-semibold text-gray-400 block">
                              {key.replace(/_/g, ' ')}
                            </span>
                            <span className="font-mono text-gray-900 dark:text-white truncate block">
                              {key === 'total_amount' && typeof val === 'number'
                                ? formatPaiseToINR(val)
                                : String(val ?? 'N/A')}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Informational Limitation Box */}
              <div className="p-3.5 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-[11px] text-gray-500 dark:text-gray-400 space-y-1">
                <strong>API Boundary Note:</strong> The backend provides specific lookup endpoints for single orders and cases, but does not provide a general list endpoint (e.g. <code>GET /cases</code>) for all historical cases. Agents should use the primary resolution workflow above for case intake and management.
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
export default AgentWorkspacePage
