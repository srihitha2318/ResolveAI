import React, { useState, useEffect } from 'react'
import { Modal } from '../common/Modal'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import { Clock, AlertCircle, RefreshCw } from 'lucide-react'
import { getCaseAuditEvents } from '../../services/api'
import type { CaseEventItem } from '../../types/analytics'

interface CaseAuditHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  caseIdentifier: string | number
  caseNumber?: string
}

export const CaseAuditHistoryModal: React.FC<CaseAuditHistoryModalProps> = ({
  isOpen,
  onClose,
  caseIdentifier,
  caseNumber,
}) => {
  const [events, setEvents] = useState<CaseEventItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadEvents = async () => {
    if (!caseIdentifier) return
    setIsLoading(true)
    setError(null)
    try {
      const resp = await getCaseAuditEvents(caseIdentifier)
      setEvents(resp.events || [])
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve case audit events.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!isOpen || !caseIdentifier) return

    let isSubscribed = true
    getCaseAuditEvents(caseIdentifier)
      .then((resp) => {
        if (isSubscribed) {
          setEvents(resp.events || [])
          setIsLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (isSubscribed) {
          const msg = err instanceof Error ? err.message : 'Failed to retrieve case audit events.'
          setError(msg)
          setIsLoading(false)
        }
      })

    return () => {
      isSubscribed = false
    }
  }, [isOpen, caseIdentifier])

  const getEventBadgeVariant = (eventType: string): 'error' | 'success' | 'pending' | 'warning' | 'neutral' => {
    switch (eventType.toLowerCase()) {
      case 'case_opened':
      case 'created':
        return 'pending'
      case 'approval_approved':
      case 'approved':
        return 'success'
      case 'approval_rejected':
      case 'rejected':
        return 'error'
      case 'sla_breach':
      case 'expired':
        return 'warning'
      case 'status_change':
      case 'clarification_requested':
        return 'neutral'
      default:
        return 'neutral'
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Audit History & Event Trail — ${caseNumber || `Case #${caseIdentifier}`}`}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pb-2 border-b border-gray-200 dark:border-dark-border">
          <span>Read-only persistent audit trail recorded from database records.</span>
          <Button
            variant="outline"
            size="sm"
            onClick={loadEvents}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>

        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="p-12 text-center text-sm text-gray-500 dark:text-gray-400">
            <div className="w-6 h-6 border-2 border-brand-forest border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading audit history...
          </div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center text-xs text-gray-500 dark:text-gray-400">
            No audit events recorded for this case yet.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200 dark:before:bg-dark-border">
            {events.map((evt) => (
              <div key={evt.id} className="relative space-y-1">
                {/* Timeline dot */}
                <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-brand-forest dark:bg-brand-sage ring-4 ring-white dark:ring-dark-card" />

                <div className="flex items-center justify-between gap-2">
                  <Badge variant={getEventBadgeVariant(evt.event_type)} size="sm">
                    {evt.event_type}
                  </Badge>
                  <span className="text-[11px] font-mono text-gray-400 dark:text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {evt.created_at ? new Date(evt.created_at).toLocaleString() : 'N/A'}
                  </span>
                </div>

                <p className="text-xs text-gray-800 dark:text-gray-200 font-medium pt-1">
                  {evt.message}
                </p>

                {evt.details_json && (
                  <div className="text-[11px] font-mono p-2 rounded bg-gray-50 dark:bg-dark-bg text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-dark-border/60 overflow-x-auto">
                    {evt.details_json}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-dark-border">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}
