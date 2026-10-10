import React, { useEffect, useState, useCallback } from 'react'
import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { ApprovalDetailModal } from '../components/supervisor/ApprovalDetailModal'
import { SupervisorAnalyticsPanel } from '../components/supervisor/SupervisorAnalyticsPanel'
import { CaseAuditHistoryModal } from '../components/supervisor/CaseAuditHistoryModal'
import { useAuth } from '../hooks/useAuth'
import { getPendingApprovals } from '../services/api'
import type { PendingApprovalItem } from '../types/workflow'
import { calculateSlaRemaining } from '../utils/dateUtils'
import { ApiError } from '../types/api'
import {
  Clock,
  AlertTriangle,
  ShieldCheck,
  CheckCircle,
  RefreshCw,
  Search,
  Eye,
  SlidersHorizontal,
  BarChart2,
  ListFilter,
  History,
} from 'lucide-react'

export const SupervisorDashboardPage: React.FC = () => {
  const { user } = useAuth()
  const [items, setItems] = useState<PendingApprovalItem[]>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successToast, setSuccessToast] = useState<string | null>(null)

  // Selected thread for inspection modal
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false)

  // Audit history modal state
  const [auditCaseId, setAuditCaseId] = useState<number | string | null>(null)
  const [auditCaseNumber, setAuditCaseNumber] = useState<string | undefined>(undefined)
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false)

  // Active view tab: 'queue' or 'analytics'
  const [activeTab, setActiveTab] = useState<'queue' | 'analytics'>('queue')

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<'all' | 'high' | 'standard'>('all')

  // Live timer tick for visual SLA countdown
  const [, setTick] = useState<number>(0)

  const fetchApprovals = useCallback(async () => {
    setIsLoading(true)
    setErrorMsg(null)
    try {
      const resp = await getPendingApprovals({ limit: 50, offset: 0 })
      setItems(resp.items || [])
      setTotalCount(resp.total_count ?? resp.items?.length ?? 0)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || 'Failed to load pending approvals from server.')
      } else {
        setErrorMsg('Network error connecting to approval queue.')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Initial fetch and 30-second polling interval
  useEffect(() => {
    let isMounted = true
    const executeFetch = async () => {
      try {
        const resp = await getPendingApprovals({ limit: 50, offset: 0 })
        if (isMounted) {
          setItems(resp.items || [])
          setTotalCount(resp.total_count ?? resp.items?.length ?? 0)
        }
      } catch (err: unknown) {
        if (isMounted) {
          if (err instanceof ApiError) {
            setErrorMsg(err.message || 'Failed to load pending approvals from server.')
          } else {
            setErrorMsg('Network error connecting to approval queue.')
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void executeFetch()

    const pollInterval = window.setInterval(() => {
      void executeFetch()
    }, 30000)

    const timerTick = window.setInterval(() => {
      setTick((prev) => prev + 1)
    }, 10000)

    return () => {
      isMounted = false
      window.clearInterval(pollInterval)
      window.clearInterval(timerTick)
    }
  }, [])

  // Filter items
  const filteredItems = items.filter((item) => {
    const q = searchQuery.toLowerCase().trim()
    const matchesSearch =
      !q ||
      item.case_number?.toLowerCase().includes(q) ||
      item.order_number?.toLowerCase().includes(q) ||
      item.customer_name?.toLowerCase().includes(q) ||
      item.requested_action?.toLowerCase().includes(q)

    const matchesPriority =
      priorityFilter === 'all' ||
      (priorityFilter === 'high' && item.sla_priority === 'high') ||
      (priorityFilter === 'standard' && item.sla_priority !== 'high')

    return matchesSearch && matchesPriority
  })

  // Accurate Summary Metrics calculated strictly from items
  const expiredCount = items.filter(
    (i) => i.is_expired || calculateSlaRemaining(i.expires_at).isExpired
  ).length

  const urgentCount = items.filter((i) => {
    const sla = calculateSlaRemaining(i.expires_at, i.is_expired)
    return !sla.isExpired && sla.isUrgent
  }).length

  const highValueCount = items.filter(
    (i) => i.required_role === 'senior_supervisor' || i.sla_priority === 'high'
  ).length

  const handleOpenDetail = (threadId: string | null) => {
    if (!threadId) return
    setSelectedThreadId(threadId)
    setIsModalOpen(true)
  }

  const handleOpenAuditModal = (caseId: number, caseNumber: string | null) => {
    setAuditCaseId(caseId)
    setAuditCaseNumber(caseNumber || undefined)
    setIsAuditModalOpen(true)
  }

  const handleDecisionSuccess = (msg: string) => {
    setSuccessToast(msg)
    fetchApprovals()
    setTimeout(() => {
      setSuccessToast(null)
    }, 6000)
  }

  return (
    <div className="min-h-screen flex flex-col bg-brand-softgray dark:bg-dark-bg text-gray-900 dark:text-gray-100 transition-colors">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {/* Workspace Hub Sidebar */}
        <Sidebar className="hidden lg:flex" />

        {/* Main Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Top Title Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-brand-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
                  Supervisor Command Console
                </h1>
                <Badge variant={user?.role === 'senior_supervisor' ? 'success' : 'pending'} size="sm">
                  {user?.role === 'senior_supervisor' ? 'Senior Authority' : 'Tier-2 Authority'}
                </Badge>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Real-time human-in-the-loop review queue &amp; SLA compliance matrix
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex bg-gray-100 dark:bg-dark-bg p-1 rounded-lg border border-gray-200 dark:border-dark-border text-xs">
                <button
                  type="button"
                  id="supervisor-tab-queue"
                  onClick={() => setActiveTab('queue')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-colors ${
                    activeTab === 'queue'
                      ? 'bg-white dark:bg-dark-card text-brand-forest dark:text-brand-sage shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
                  }`}
                >
                  <ListFilter className="w-3.5 h-3.5" />
                  <span>Approvals Queue ({totalCount})</span>
                </button>
                <button
                  type="button"
                  id="supervisor-tab-analytics"
                  onClick={() => setActiveTab('analytics')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-semibold transition-colors ${
                    activeTab === 'analytics'
                      ? 'bg-white dark:bg-dark-card text-brand-forest dark:text-brand-sage shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
                  }`}
                >
                  <BarChart2 className="w-3.5 h-3.5" />
                  <span>Operational Analytics</span>
                </button>
              </div>

              {activeTab === 'queue' && (
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
                  onClick={fetchApprovals}
                  disabled={isLoading}
                  className="text-xs font-semibold"
                >
                  Refresh
                </Button>
              )}
            </div>
          </div>

          {/* Success Toast Banner */}
          {successToast && (
            <div
              className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-xs text-emerald-900 dark:text-emerald-200 flex items-center justify-between shadow-subtle animate-in fade-in"
              role="status"
            >
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>{successToast}</span>
              </div>
              <button
                type="button"
                onClick={() => setSuccessToast(null)}
                className="text-emerald-600 dark:text-emerald-400 hover:underline text-[11px]"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Error Banner */}
          {errorMsg && (
            <div
              className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-xs text-rose-900 dark:text-rose-200 flex items-center justify-between shadow-subtle"
              role="alert"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
                <span>{errorMsg}</span>
              </div>
              <Button variant="outline" size="sm" onClick={fetchApprovals} className="text-xs">
                Retry
              </Button>
            </div>
          )}

          {/* Active View: Analytics vs Queue */}
          {activeTab === 'analytics' ? (
            <SupervisorAnalyticsPanel />
          ) : (
            <>
              {/* Metrics Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Pending Approvals */}
            <Card variant="default">
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Pending Queue</span>
                  <ShieldCheck className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                </div>
                <div className="text-2xl font-bold font-mono text-gray-900 dark:text-white">
                  {totalCount}
                </div>
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  Awaiting supervisor action
                </div>
              </CardContent>
            </Card>

            {/* 2. Approaching SLA */}
            <Card variant="default">
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>In Jeopardy (&lt; 2h)</span>
                  <Clock className="w-4 h-4 text-amber-500" />
                </div>
                <div className="text-2xl font-bold font-mono text-amber-600 dark:text-amber-400">
                  {urgentCount}
                </div>
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  Approaching target SLA
                </div>
              </CardContent>
            </Card>

            {/* 3. Expired / SLA Breached */}
            <Card variant="default">
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Expired Approvals</span>
                  <AlertTriangle className="w-4 h-4 text-status-error" />
                </div>
                <div className="text-2xl font-bold font-mono text-status-error">
                  {expiredCount}
                </div>
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  Requires Senior Override
                </div>
              </CardContent>
            </Card>

            {/* 4. High-Value Cases */}
            <Card variant="default">
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>High-Value Claims</span>
                  <SlidersHorizontal className="w-4 h-4 text-brand-sage" />
                </div>
                <div className="text-2xl font-bold font-mono text-brand-forest dark:text-brand-sage">
                  {highValueCount}
                </div>
                <div className="text-[11px] text-gray-500 dark:text-gray-400">
                  &gt; ₹25,000 threshold
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Table Card with Filter Controls */}
          <Card variant="default">
            <CardHeader className="p-4 border-b border-gray-100 dark:border-dark-border/60">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <CardTitle className="text-base">Pending Resolution Cases</CardTitle>

                {/* Search & Priority Filter */}
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    <input
                      type="text"
                      placeholder="Filter case, order, or customer..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-gray-50 dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-forest"
                    />
                  </div>

                  <select
                    value={priorityFilter}
                    onChange={(e) => setPriorityFilter(e.target.value as 'all' | 'high' | 'standard')}
                    aria-label="Filter by SLA priority"
                    className="py-1.5 px-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-gray-50 dark:bg-dark-bg text-gray-800 dark:text-gray-200 focus:outline-none"
                  >
                    <option value="all">All Priorities</option>
                    <option value="high">High Priority</option>
                    <option value="standard">Standard Priority</option>
                  </select>
                </div>
              </div>
            </CardHeader>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-dark-border bg-gray-50/70 dark:bg-dark-bg/60 text-gray-500 dark:text-gray-400 font-semibold uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Case #</th>
                    <th className="py-3 px-4">Order #</th>
                    <th className="py-3 px-4">Customer</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">SLA Deadline &amp; Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-dark-border/60">
                  {filteredItems.length === 0 && !isLoading && (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-gray-400 dark:text-gray-500">
                        <div className="max-w-xs mx-auto space-y-2">
                          <CheckCircle className="w-8 h-8 mx-auto text-emerald-500/70" />
                          <p className="font-semibold text-gray-700 dark:text-gray-300">
                            Approval Queue is Clean
                          </p>
                          <p className="text-[11px]">
                            {searchQuery
                              ? 'No cases match your search criteria.'
                              : 'No complaint cases are currently awaiting supervisor approval.'}
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}

                  {filteredItems.map((item) => {
                    const isExp =
                      item.is_expired || calculateSlaRemaining(item.expires_at).isExpired
                    const slaInfo = calculateSlaRemaining(item.expires_at, isExp)

                    return (
                      <tr
                        key={item.id}
                        className="hover:bg-gray-50/80 dark:hover:bg-dark-cardHover transition-colors"
                      >
                        <td className="py-3 px-4 font-mono font-bold text-gray-900 dark:text-white">
                          {item.case_number || `Case #${item.case_id}`}
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-600 dark:text-gray-300">
                          {item.order_number || '—'}
                        </td>
                        <td className="py-3 px-4 text-gray-700 dark:text-gray-300 font-medium">
                          {item.customer_name || '—'}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="neutral" size="sm">
                            {item.requested_action}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={item.sla_priority === 'high' ? 'warning' : 'neutral'}
                            size="sm"
                          >
                            {item.sla_priority || 'Standard'}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div className="space-y-0.5">
                            <Badge
                              variant={
                                slaInfo.isExpired
                                  ? 'error'
                                  : slaInfo.isUrgent
                                  ? 'warning'
                                  : 'success'
                              }
                              size="sm"
                              dot
                            >
                              {slaInfo.formatted}
                            </Badge>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              leftIcon={<History className="w-3.5 h-3.5" />}
                              onClick={() => handleOpenAuditModal(item.case_id, item.case_number)}
                              className="text-xs text-gray-600 hover:text-gray-900 dark:text-gray-400"
                              title="View chronological audit event history"
                            >
                              Audit
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              leftIcon={<Eye className="w-3.5 h-3.5" />}
                              onClick={() => handleOpenDetail(item.thread_id)}
                              className="text-xs font-semibold"
                            >
                              Inspect
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
          </>
          )}

          {/* Audit History Modal */}
          {isAuditModalOpen && auditCaseId && (
            <CaseAuditHistoryModal
              isOpen={isAuditModalOpen}
              onClose={() => setIsAuditModalOpen(false)}
              caseIdentifier={auditCaseId}
              caseNumber={auditCaseNumber}
            />
          )}
        </div>
      </div>

      {/* Investigation Details & Decision Dialog */}
      <ApprovalDetailModal
        isOpen={isModalOpen}
        threadId={selectedThreadId}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedThreadId(null)
        }}
        onDecisionSuccess={handleDecisionSuccess}
      />
    </div>
  )
}
