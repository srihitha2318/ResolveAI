import React, { useState, useEffect } from 'react'
import { Card } from '../common/Card'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import {
  BarChart3,
  PieChart as PieChartIcon,
  TrendingUp,
  AlertTriangle,
  Clock,
  RefreshCw,
  FolderOpen,
  HelpCircle,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { getAnalyticsOverview } from '../../services/api'
import type { AnalyticsOverviewResponse } from '../../types/analytics'

const CATEGORY_COLORS = ['#174C3C', '#72A58B', '#D97706', '#4F46E5', '#64748B']
const STATUS_COLORS: Record<string, string> = {
  open: '#3B82F6',
  in_progress: '#8B5CF6',
  resolved: '#10B981',
  closed: '#6B7280',
  escalated: '#F59E0B',
}

export const SupervisorAnalyticsPanel: React.FC = () => {
  const [data, setData] = useState<AnalyticsOverviewResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalytics = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const resp = await getAnalyticsOverview()
      setData(resp)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve operational metrics.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isSubscribed = true
    getAnalyticsOverview()
      .then((resp) => {
        if (isSubscribed) {
          setData(resp)
          setIsLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (isSubscribed) {
          const msg = err instanceof Error ? err.message : 'Failed to retrieve operational metrics.'
          setError(msg)
          setIsLoading(false)
        }
      })

    return () => {
      isSubscribed = false
    }
  }, [])


  if (isLoading) {
    return (
      <Card className="p-16 text-center text-sm text-gray-500 dark:text-gray-400">
        <div className="w-8 h-8 border-2 border-brand-forest border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Calculating operational metrics from backend database...
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card className="p-8 text-center space-y-4">
        <div className="text-red-600 dark:text-red-400 font-semibold text-sm">
          {error || 'Unable to load analytics data.'}
        </div>
        <Button variant="outline" size="sm" onClick={fetchAnalytics}>
          Retry
        </Button>
      </Card>
    )
  }

  const statusPieData = data.status_distribution
    .filter((s) => s.count > 0)
    .map((s) => ({
      name: s.status.replace('_', ' ').toUpperCase(),
      value: s.count,
      statusKey: s.status,
    }))

  const categoryBarData = data.category_distribution.map((c) => ({
    name: c.category.replace('_', ' '),
    cases: c.count,
  }))

  return (
    <div className="space-y-8">
      {/* KPI Stat Cards Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Cases */}
        <Card className="p-5 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Total Filed Cases
            </p>
            <p className="text-2xl font-extrabold text-gray-900 dark:text-white">
              {data.total_cases}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {data.open_cases} open · {data.in_progress_cases} in progress
            </p>
          </div>
          <div className="p-3 rounded-xl bg-brand-forest/10 dark:bg-brand-forest/30 text-brand-forest dark:text-brand-sage">
            <FolderOpen className="w-6 h-6" />
          </div>
        </Card>

        {/* Pending Approvals */}
        <Card className="p-5 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Pending Approvals
            </p>
            <p className="text-2xl font-extrabold text-amber-600 dark:text-amber-400">
              {data.pending_approvals}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {data.approved_count} approved · {data.rejected_count} rejected
            </p>
          </div>
          <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400">
            <Clock className="w-6 h-6" />
          </div>
        </Card>

        {/* SLA Breaches */}
        <Card className="p-5 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              SLA Breaches
            </p>
            <p className={`text-2xl font-extrabold ${data.sla_breaches > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
              {data.sla_breaches}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {data.sla_breaches === 0 ? 'Zero overdue claims' : 'Requires Senior Override'}
            </p>
          </div>
          <div className={`p-3 rounded-xl ${data.sla_breaches > 0 ? 'bg-rose-50 dark:bg-rose-950/40 text-rose-600' : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600'}`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
        </Card>

        {/* Clarification Paused */}
        <Card className="p-5 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Awaiting Information
            </p>
            <p className="text-2xl font-extrabold text-blue-600 dark:text-blue-400">
              {data.pending_clarifications}
            </p>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Paused workflow threads
            </p>
          </div>
          <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
            <HelpCircle className="w-6 h-6" />
          </div>
        </Card>
      </div>

      {/* Visual Analytics Charts Strip */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Case Volume by Product Category */}
        <Card className="p-6 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                Case Distribution by Category
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Breakdown of marketplace orders generating support tickets
              </p>
            </div>
          </div>

          <div className="h-64 w-full pt-2">
            {categoryBarData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">
                No category data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryBarData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#174C3C',
                      borderColor: '#72A58B',
                      borderRadius: 8,
                      color: '#ffffff',
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="cases" fill="#174C3C" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* Case Status Distribution */}
        <Card className="p-6 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <PieChartIcon className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                Workflow & Case Status Ratios
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Proportion of cases by current operational stage
              </p>
            </div>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            {statusPieData.length === 0 ? (
              <div className="text-xs text-gray-400">No status data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {statusPieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={STATUS_COLORS[entry.statusKey] || CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      borderRadius: 8,
                      color: '#ffffff',
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* Recent Case Log Feed */}
      <Card className="p-6 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
              Recent Support Case Activity
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Live chronological feed of support cases persisted in the database
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchAnalytics}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh Metrics
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 dark:bg-dark-bg text-gray-500 dark:text-gray-400 font-semibold border-b border-gray-200 dark:border-dark-border">
              <tr>
                <th className="py-2.5 px-3">Case Number</th>
                <th className="py-2.5 px-3">Subject</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Logged Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-dark-border">
              {data.recent_activity.map((caseItem) => (
                <tr key={caseItem.case_number} className="hover:bg-gray-50/50 dark:hover:bg-dark-bg/50">
                  <td className="py-2.5 px-3 font-bold font-mono text-gray-900 dark:text-white">
                    {caseItem.case_number}
                  </td>
                  <td className="py-2.5 px-3 text-gray-700 dark:text-gray-300 max-w-xs truncate">
                    {caseItem.subject}
                  </td>
                  <td className="py-2.5 px-3">
                    <Badge
                      variant={
                        caseItem.status === 'resolved'
                          ? 'success'
                          : caseItem.status === 'in_progress'
                          ? 'pending'
                          : caseItem.status === 'escalated'
                          ? 'warning'
                          : 'neutral'
                      }
                      size="sm"
                    >
                      {caseItem.status}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-gray-500 dark:text-gray-400 font-mono">
                    {caseItem.created_at ? new Date(caseItem.created_at).toLocaleDateString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
