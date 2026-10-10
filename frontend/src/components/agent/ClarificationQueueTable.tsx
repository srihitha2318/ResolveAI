import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../common/Card'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import { HelpCircle, RefreshCw, AlertCircle } from 'lucide-react'
import { getPendingClarifications } from '../../services/api'
import type { PendingClarificationItem } from '../../types/workflow'
import { ApiError } from '../../types/api'

export const ClarificationQueueTable: React.FC = () => {
  const [items, setItems] = useState<PendingClarificationItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchClarifications = useCallback(async () => {
    setIsLoading(true)
    setErrorMsg(null)
    try {
      const resp = await getPendingClarifications({ limit: 50, offset: 0 })
      setItems(resp.items || [])
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || 'Unable to retrieve pending clarifications queue.')
      } else {
        setErrorMsg('Failed to connect to clarifications service.')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    getPendingClarifications({ limit: 50, offset: 0 })
      .then((resp) => {
        if (active) {
          setItems(resp.items || [])
          setIsLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (active) {
          if (err instanceof ApiError) {
            setErrorMsg(err.message || 'Unable to retrieve pending clarifications queue.')
          } else {
            setErrorMsg('Failed to connect to clarifications service.')
          }
          setIsLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  const filteredItems = items.filter((item) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    return (
      (item.thread_id && item.thread_id.toLowerCase().includes(term)) ||
      (item.case_number && item.case_number.toLowerCase().includes(term)) ||
      (item.order_number && item.order_number.toLowerCase().includes(term)) ||
      (item.missing_information &&
        item.missing_information.some((m) => m.toLowerCase().includes(term)))
    )
  })

  return (
    <Card variant="default">
      <CardHeader className="pb-3 border-b border-gray-100 dark:border-dark-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
            <div>
              <CardTitle className="text-base">Pending Clarifications Queue</CardTitle>
              <CardDescription>
                Workflow cases currently paused awaiting required customer information
              </CardDescription>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-gray-300">
              {items.length} Active
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchClarifications}
              isLoading={isLoading}
              className="text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Search filter */}
        <div className="flex items-center justify-between gap-3">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter by thread, case, order, or missing field..."
            className="w-full sm:max-w-xs px-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage"
          />
        </div>

        {/* Error banner */}
        {errorMsg && (
          <div
            className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2"
            role="alert"
          >
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Table / List */}
        {isLoading ? (
          <div className="py-8 text-center text-xs text-gray-500 space-y-2">
            <RefreshCw className="w-5 h-5 mx-auto animate-spin text-brand-forest dark:text-brand-sage" />
            <p>Loading paused clarification threads...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="py-8 text-center text-xs text-gray-500 border border-dashed border-gray-200 dark:border-dark-border rounded-lg space-y-1">
            <p className="font-semibold text-gray-700 dark:text-gray-300">
              {searchTerm ? 'No matching clarification cases found' : 'No Paused Clarifications'}
            </p>
            <p className="text-[11px] text-gray-400">
              {searchTerm
                ? 'Try clearing your search filters'
                : 'All workflows are actively proceeding without pending customer questions'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-dark-border">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 dark:bg-dark-bg text-gray-500 dark:text-gray-400 font-semibold border-b border-gray-200 dark:border-dark-border">
                <tr>
                  <th className="px-3 py-2.5">Thread ID</th>
                  <th className="px-3 py-2.5">Case / Order</th>
                  <th className="px-3 py-2.5">Missing Information</th>
                  <th className="px-3 py-2.5">Created At</th>
                  <th className="px-3 py-2.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-dark-border/60">
                {filteredItems.map((item) => (
                  <tr
                    key={item.thread_id}
                    className="hover:bg-gray-50/50 dark:hover:bg-dark-cardHover transition-colors"
                  >
                    <td className="px-3 py-2.5 font-mono text-[11px] text-gray-800 dark:text-gray-200">
                      {item.thread_id.substring(0, 16)}...
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {item.case_number || (item.case_id ? `Case #${item.case_id}` : 'Unassigned')}
                      </div>
                      <span className="text-[11px] font-mono text-gray-400">
                        {item.order_number || 'No order'}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {item.missing_information && item.missing_information.length > 0 ? (
                          item.missing_information.map((m, idx) => (
                            <span
                              key={idx}
                              className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-300 font-mono text-[10px]"
                            >
                              {m}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 italic text-[11px]">Unspecified</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-gray-500 text-[11px] whitespace-nowrap">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-3 py-2.5 text-right whitespace-nowrap">
                      <Badge variant="pending" size="sm" dot>
                        Awaiting Input
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
