/**
 * TypeScript definitions for ResolveAI Operational Analytics and Case Events.
 */

export interface CategoryBreakdown {
  category: string
  count: number
}

export interface StatusBreakdown {
  status: string
  count: number
}

export interface RecentCaseActivity {
  case_number: string
  subject: string
  status: string
  created_at: string
}

export interface AnalyticsOverviewResponse {
  total_cases: number
  open_cases: number
  in_progress_cases: number
  resolved_cases: number
  closed_cases: number
  escalated_cases: number
  pending_approvals: number
  approved_count: number
  rejected_count: number
  sla_breaches: number
  pending_clarifications: number
  category_distribution: CategoryBreakdown[]
  status_distribution: StatusBreakdown[]
  recent_activity: RecentCaseActivity[]
}

export interface CaseEventItem {
  id: number
  case_id: number
  event_type: string
  message: string
  details_json?: string | null
  created_at: string
}

export interface CaseEventsListResponse {
  case_id: number
  events: CaseEventItem[]
}
