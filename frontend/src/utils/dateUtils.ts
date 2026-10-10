/**
 * Date and SLA calculation utilities
 */

export interface SlaTimeRemaining {
  isExpired: boolean
  isUrgent: boolean // less than 2 hours remaining
  formatted: string
  totalMinutes: number
}

export function calculateSlaRemaining(
  expiresAtIso: string | null | undefined,
  backendIsExpired = false
): SlaTimeRemaining {
  if (backendIsExpired) {
    return {
      isExpired: true,
      isUrgent: true,
      formatted: 'SLA Breached (Expired)',
      totalMinutes: -1,
    }
  }

  if (!expiresAtIso) {
    return {
      isExpired: false,
      isUrgent: false,
      formatted: 'No SLA Deadline',
      totalMinutes: 99999,
    }
  }

  const targetDate = new Date(expiresAtIso)
  if (isNaN(targetDate.getTime())) {
    return {
      isExpired: false,
      isUrgent: false,
      formatted: 'Invalid Timestamp',
      totalMinutes: 0,
    }
  }

  const now = new Date()
  const diffMs = targetDate.getTime() - now.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))

  if (diffMinutes <= 0) {
    return {
      isExpired: true,
      isUrgent: true,
      formatted: 'SLA Breached (Expired)',
      totalMinutes: diffMinutes,
    }
  }

  const hours = Math.floor(diffMinutes / 60)
  const mins = diffMinutes % 60
  const isUrgent = diffMinutes < 120 // less than 2 hours

  let formatted = ''
  if (hours > 0) {
    formatted = `${hours}h ${mins}m remaining`
  } else {
    formatted = `${mins}m remaining`
  }

  return {
    isExpired: false,
    isUrgent,
    formatted,
    totalMinutes: diffMinutes,
  }
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—'
  const date = new Date(isoString)
  if (isNaN(date.getTime())) return isoString
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
