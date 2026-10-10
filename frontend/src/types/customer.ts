/**
 * TypeScript definitions for ResolveAI Customer Portal.
 */

export interface CustomerVerifyAccessRequest {
  email: string
  order_number?: string
  case_number?: string
}

export interface CustomerCaseSummary {
  case_number: string
  order_number?: string | null
  product_name?: string | null
  subject: string
  status: string
  created_at: string
  clarification_needed: boolean
  thread_id?: string | null
}

export interface CustomerAccessResponse {
  access_token: string
  token_type: string
  customer_id: number
  customer_name: string
  customer_email: string
  cases: CustomerCaseSummary[]
}

export interface CustomerCaseDetail {
  case_number: string
  order_number?: string | null
  product_name?: string | null
  order_status?: string | null
  delivery_status?: string | null
  subject: string
  complaint_text: string
  status: string
  priority: string
  resolution_summary?: string | null
  ticket_number?: string | null
  created_at: string
  updated_at: string
  clarification_needed: boolean
  thread_id?: string | null
  clarification_prompt?: string | null
  missing_fields: string[]
}
