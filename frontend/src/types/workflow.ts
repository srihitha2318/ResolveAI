/**
 * Workflow, Approval, and SLA type contracts matching backend schemas
 */

import type { UserRole } from './auth'

export interface PendingApprovalItem {
  id: number
  case_id: number
  case_number: string | null
  order_number: string | null
  customer_name: string | null
  thread_id: string | null
  requested_action: string
  status: string
  workflow_status: string
  justification: string
  proposed_resolution: string | null
  policy_evidence: string | null
  expires_at: string | null
  sla_priority: string | null
  required_role: UserRole | string | null
  is_expired: boolean
  created_at: string
  updated_at: string
}

export interface PendingApprovalsResponse {
  total_count: number
  limit: number
  offset: number
  items: PendingApprovalItem[]
}

export interface OrderDetail {
  order_number: string
  product_name: string
  total_amount: number // in paise or rupees depending on endpoint
  currency: string
  delivery_status: string
}

export interface CustomerDetail {
  name: string
  email: string
}

export interface CaseDetail {
  id: number | null
  case_number: string | null
  subject: string | null
  complaint_text: string | null
  status: string | null
  priority: string | null
}

export interface ApprovalDetailResponse {
  id: number
  case_id: number
  case_number: string | null
  thread_id: string | null
  requested_action: string
  status: string
  workflow_status: string
  justification: string
  proposed_resolution: string | null
  policy_evidence: string | null
  reviewer_id: string | null
  decision_reason: string | null
  decision_timestamp: string | null
  expires_at: string | null
  sla_priority: string | null
  required_role: UserRole | string | null
  is_expired: boolean
  created_at: string
  updated_at: string
  case: CaseDetail | null
  order: OrderDetail | null
  customer: CustomerDetail | null
}

export interface ApprovalDecisionRequest {
  reviewer_id: string
  reason?: string | null
  override_expired?: boolean
}

export interface ApprovalDecisionResponse {
  id: number
  case_id: number
  thread_id: string
  status: string
  workflow_status: string
  reviewer_id: string
  decision_reason: string | null
  decision_timestamp: string
  is_expired_override?: boolean
  workflow_result?: WorkflowResolveResponse | null
}

// ---------------------------------------------------------------------------
// Agent Investigation Schemas
// ---------------------------------------------------------------------------

export interface ComplaintAnalysisResult {
  category: string
  main_issue: string
  desired_outcome: string | null
  order_number: string | null
  image_relevant: boolean
  additional_info_required: boolean
  analysis_method: string
  limitations: string | null
}

export interface OrderInvestigationDetails {
  id: number
  order_number: string
  product_name: string
  order_status: string
  delivery_status: string
  order_date: string | null
  expected_delivery_date: string | null
  delivered_at: string | null
  total_amount: number // in integer paise
  currency: string
  customer_id: number
  seller_id: string | null
  category: string | null
  total_amount_formatted: string | null
}

export interface PreviousCaseItem {
  id: number
  case_number: string
  order_id: number | null
  subject: string
  status: string
  priority: string
  created_at: string | null
}

export interface OrderInvestigationResult {
  order_exists: boolean
  order_number: string | null
  order_details: OrderInvestigationDetails | null
  delivery_summary: string | null
  previous_cases: PreviousCaseItem[]
  refund_status: string
  missing_information: string[]
  limitations: string
}

export interface PolicyPassageItem {
  document_name: string
  passage: string
  matched_terms: string[]
  line_number: number | null
  policy_id: string | null
  scope: string | null
}

export interface PolicyRetrievalResult {
  query: string
  passages: PolicyPassageItem[]
  found_relevant: boolean
  retrieval_method: string
  explanation: string
  policy_ids: string[]
  source_files: string[]
  conflict_status: string | null
  needs_review: boolean
  insufficient_evidence: boolean
}

export interface ResolutionRecommendationResult {
  recommendation_type: string
  title: string
  reasoning: string
  action_required: string
  human_approval_required: boolean
  missing_information: string[]
  evidence_used: string[]
  method: string
}

export interface VerificationResult {
  verification_status: 'pass' | 'fail' | string
  is_valid: boolean
  detected_issues: string[]
  evidence_checked: string[]
  missing_evidence: string[]
  required_next_step: string
}

// ---------------------------------------------------------------------------
// Workflow Execution Payload & Response
// ---------------------------------------------------------------------------

export interface WorkflowResolveRequest {
  complaint_text: string
  order_number?: string | null
  case_number?: string | null
  case_id?: number | null
  customer_id?: number | null
  category?: string | null
  seller_id?: string | null
}

export interface WorkflowResolveResponse {
  workflow_id: string
  thread_id: string | null
  case_id: number | null
  case_number: string | null
  status: 'completed' | 'needs_information' | 'needs_review' | 'rejected' | 'failed' | string
  current_stage: string
  complaint_analysis: ComplaintAnalysisResult | null
  order_investigation: OrderInvestigationResult | null
  policy_evidence: PolicyRetrievalResult | null
  retrieval_method: string | null
  recommended_resolution: ResolutionRecommendationResult | null
  verification_result: VerificationResult | null
  needs_review: boolean
  escalation_reason: string | null
  supervisor_decision: string | null
  missing_information: string[]
  clarification_details: Record<string, string> | null
  errors: string[]
  retry_count: number
  events_recorded: Array<Record<string, unknown>>
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Support Ticket & Audit Event Schemas
// ---------------------------------------------------------------------------

export interface CreateTicketRequest {
  category: string
}

export interface CreateTicketResponse {
  ticket_id: number
  ticket_number: string
  case_id: number
  category: string
  status: string
  created_at: string
  is_duplicate?: boolean
}

export interface CreateEventRequest {
  event_type: string
  message: string
  details_json?: string | null
}

export interface CreateEventResponse {
  event_id: number
  case_id: number
  event_type: string
  message: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Clarification Queue Schemas (Level 6 Phase 3/4)
// ---------------------------------------------------------------------------

export interface PendingClarificationItem {
  id?: number
  thread_id: string
  case_id: number | null
  case_number: string | null
  customer_id: number | null
  order_number: string | null
  complaint_text?: string | null
  missing_information: string[]
  clarification_details: Record<string, string> | null
  created_at: string
  updated_at: string
}

export interface PendingClarificationsResponse {
  total_count: number
  limit: number
  offset: number
  items: PendingClarificationItem[]
}

export interface ProvideInformationRequest {
  order_number?: string | null
  additional_details?: string | null
  customer_id?: number | null
  customer_email?: string | null
  category?: string | null
  seller_id?: string | null
}

export interface ProvideInformationResponse {
  thread_id: string
  case_id?: number | null
  status: string
  workflow_status: string
  message: string
  missing_information?: string[]
  clarification_details?: Record<string, string> | null
  workflow_result?: WorkflowResolveResponse | null
}


