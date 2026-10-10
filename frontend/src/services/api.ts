import { ApiError, type RequestOptions, type SystemStatusResponse, type HealthProbeResponse } from '../types/api'
import type { LoginRequest, TokenResponse, UserResponse } from '../types/auth'
import type {
  PendingApprovalsResponse,
  ApprovalDetailResponse,
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  WorkflowResolveRequest,
  WorkflowResolveResponse,
  CreateTicketRequest,
  CreateTicketResponse,
  PendingClarificationsResponse,
  ProvideInformationRequest,
  ProvideInformationResponse,
} from '../types/workflow'
import type {
  CustomerVerifyAccessRequest,
  CustomerAccessResponse,
  CustomerCaseSummary,
  CustomerCaseDetail,
} from '../types/customer'
import type { AnalyticsOverviewResponse, CaseEventsListResponse } from '../types/analytics'

/**
 * Base URL for API requests.
 * Uses VITE_API_BASE_URL if configured for production;
 * falls back to relative '/api' forwarded via Vite development proxy.
 */
const rawBaseUrl = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL
  ? String(import.meta.env.VITE_API_BASE_URL).trim()
  : ''

const getBaseApiUrl = (): string => {
  if (!rawBaseUrl) return '/api'
  const trimmed = rawBaseUrl.replace(/\/+$/, '')
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}

export const API_BASE_URL = getBaseApiUrl()
const TOKEN_STORAGE_KEY = 'resolveai_staff_token'

/**
 * In-memory / sessionStorage token helpers
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setAuthToken(token: string | null): void {
  if (typeof window === 'undefined') return
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  } catch {
    // Storage access issue
  }
}

export function clearAuthToken(): void {
  setAuthToken(null)
}

const CUSTOMER_TOKEN_STORAGE_KEY = 'resolveai_customer_token'

export function getCustomerToken(): string | null {
  if (typeof window === 'undefined') return null
  try {
    return sessionStorage.getItem(CUSTOMER_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setCustomerToken(token: string | null): void {
  if (typeof window === 'undefined') return
  try {
    if (token) {
      sessionStorage.setItem(CUSTOMER_TOKEN_STORAGE_KEY, token)
    } else {
      sessionStorage.removeItem(CUSTOMER_TOKEN_STORAGE_KEY)
    }
  } catch {
    // Storage access issue
  }
}

export function clearCustomerToken(): void {
  setCustomerToken(null)
}

/**
 * Core HTTP client with typed error handling, JSON parsing, automatic token injection,
 * and AbortSignal support.
 */
export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, body, headers, ...customConfig } = options

  // Construct URL with optional query parameters
  let url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    const queryString = searchParams.toString()
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString
    }
  }

  // Attach token if present and not already provided
  const isCustomerEndpoint = url.includes('/v1/customer')
  const token = isCustomerEndpoint ? (getCustomerToken() ?? getAuthToken()) : getAuthToken()
  const authHeader: Record<string, string> = {}
  if (token) {
    authHeader['Authorization'] = `Bearer ${token}`
  }

  const reqHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...authHeader,
    ...(headers as Record<string, string>),
  }

  const config: RequestInit = {
    ...customConfig,
    headers: reqHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }

  let response: Response
  try {
    response = await fetch(url, config)
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    const message = error instanceof Error ? error.message : 'Network request failed'
    console.warn('[ApiClient] Network error encountered:', message)
    throw new ApiError('Unable to connect to the ResolveAI service. Please verify server status.', 0)
  }

  // If receiving 401 on an authenticated call, invalidate stored token
  if (response.status === 401 && token) {
    clearAuthToken()
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T
  }

  // Parse JSON response or fallback to text
  let responseData: unknown
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try {
      responseData = await response.json()
    } catch {
      responseData = null
    }
  } else {
    try {
      responseData = await response.text()
    } catch {
      responseData = null
    }
  }

  // Handle non-2xx HTTP errors
  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`
    if (responseData && typeof responseData === 'object' && 'detail' in responseData) {
      const detail = (responseData as { detail: unknown }).detail
      errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail)
    } else if (responseData && typeof responseData === 'object' && 'message' in responseData) {
      errorMessage = String((responseData as { message: unknown }).message)
    }

    throw new ApiError(errorMessage, response.status, responseData)
  }

  return responseData as T
}

/**
 * Convenience HTTP method helpers
 */
export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: 'POST', body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: 'PUT', body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: 'DELETE' }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiClient<T>(endpoint, { ...options, method: 'PATCH', body }),
}

// ---------------------------------------------------------------------------
// Authentication API Endpoints
// ---------------------------------------------------------------------------

/**
 * Authenticates user credentials against POST /api/v1/auth/login.
 */
export async function loginStaff(payload: LoginRequest): Promise<TokenResponse> {
  const result = await api.post<TokenResponse>('/v1/auth/login', payload)
  if (result.access_token) {
    setAuthToken(result.access_token)
  }
  return result
}

/**
 * Retrieves authenticated user profile via GET /api/v1/auth/me.
 */
export async function getCurrentUserProfile(signal?: AbortSignal): Promise<UserResponse> {
  return api.get<UserResponse>('/v1/auth/me', { signal })
}

// ---------------------------------------------------------------------------
// Supervisor Workflow Approval API Endpoints
// ---------------------------------------------------------------------------

/**
 * Retrieves paginated list of approval requests awaiting review via GET /api/v1/workflows/pending-approvals.
 */
export async function getPendingApprovals(
  params?: { limit?: number; offset?: number },
  signal?: AbortSignal
): Promise<PendingApprovalsResponse> {
  return api.get<PendingApprovalsResponse>('/v1/workflows/pending-approvals', {
    params: { limit: params?.limit ?? 50, offset: params?.offset ?? 0 },
    signal,
  })
}

/**
 * Retrieves full investigation facts and evidence for an approval thread via GET /api/v1/workflows/{thread_id}/approval.
 */
export async function getApprovalDetails(
  threadId: string,
  signal?: AbortSignal
): Promise<ApprovalDetailResponse> {
  return api.get<ApprovalDetailResponse>(`/v1/workflows/${encodeURIComponent(threadId)}/approval`, { signal })
}

/**
 * Submits supervisor approval decision via POST /api/v1/workflows/{thread_id}/approve.
 */
export async function approveWorkflow(
  threadId: string,
  payload: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  return api.post<ApprovalDecisionResponse>(`/v1/workflows/${encodeURIComponent(threadId)}/approve`, payload)
}

/**
 * Submits supervisor rejection decision via POST /api/v1/workflows/{thread_id}/reject.
 */
export async function rejectWorkflow(
  threadId: string,
  payload: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  return api.post<ApprovalDecisionResponse>(`/v1/workflows/${encodeURIComponent(threadId)}/reject`, payload)
}

// ---------------------------------------------------------------------------
// Support Agent Workflow & Case Tools
// ---------------------------------------------------------------------------

/**
 * Executes the autonomous complaint resolution workflow via POST /api/v1/workflows/resolve.
 */
export async function resolveComplaint(
  payload: WorkflowResolveRequest,
  signal?: AbortSignal
): Promise<WorkflowResolveResponse> {
  return api.post<WorkflowResolveResponse>('/v1/workflows/resolve', payload, { signal })
}

/**
 * Creates an authorized support ticket linked to an existing case via POST /api/v1/cases/{case_id}/tickets.
 */
export async function createTicketForCase(
  caseId: number,
  payload: CreateTicketRequest
): Promise<CreateTicketResponse> {
  return api.post<CreateTicketResponse>(`/v1/cases/${encodeURIComponent(caseId)}/tickets`, payload)
}

/**
 * Retrieves paginated list of workflow threads paused awaiting clarification via GET /api/v1/workflows/pending-clarifications.
 */
export async function getPendingClarifications(
  params?: { limit?: number; offset?: number },
  signal?: AbortSignal
): Promise<PendingClarificationsResponse> {
  return api.get<PendingClarificationsResponse>('/v1/workflows/pending-clarifications', {
    params: { limit: params?.limit ?? 50, offset: params?.offset ?? 0 },
    signal,
  })
}

/**
 * Retrieves order facts by order number via GET /api/v1/orders/{order_number}.
 */
export async function getOrderDetails(
  orderNumber: string,
  signal?: AbortSignal
): Promise<Record<string, unknown>> {
  return api.get<Record<string, unknown>>(`/v1/orders/${encodeURIComponent(orderNumber)}`, { signal })
}

/**
 * Retrieves support case details by case number via GET /api/v1/cases/{case_number}.
 */
export async function getCaseDetails(
  caseNumber: string,
  signal?: AbortSignal
): Promise<Record<string, unknown>> {
  return api.get<Record<string, unknown>>(`/v1/cases/${encodeURIComponent(caseNumber)}`, { signal })
}

// ---------------------------------------------------------------------------
// Customer Portal API Endpoints
// ---------------------------------------------------------------------------

/**
 * Verifies customer registered email and order/case ownership to create a safe session.
 */
export async function verifyCustomerAccess(
  payload: CustomerVerifyAccessRequest,
  signal?: AbortSignal
): Promise<CustomerAccessResponse> {
  const result = await api.post<CustomerAccessResponse>('/v1/customer/verify-access', payload, { signal })
  if (result.access_token) {
    setCustomerToken(result.access_token)
  }
  return result
}

/**
 * Retrieves authorized cases for the logged-in customer.
 */
export async function getCustomerCases(signal?: AbortSignal): Promise<CustomerCaseSummary[]> {
  return api.get<CustomerCaseSummary[]>('/v1/customer/cases', { signal })
}

/**
 * Retrieves sanitized case details for an authorized customer.
 */
export async function getCustomerCaseDetail(
  caseNumber: string,
  signal?: AbortSignal
): Promise<CustomerCaseDetail> {
  return api.get<CustomerCaseDetail>(`/v1/customer/cases/${encodeURIComponent(caseNumber)}`, { signal })
}

/**
 * Submits customer clarification response to resume paused LangGraph workflow.
 */
export async function submitCustomerClarification(
  threadId: string,
  payload: ProvideInformationRequest,
  signal?: AbortSignal
): Promise<ProvideInformationResponse> {
  return api.post<ProvideInformationResponse>(
    `/v1/workflows/${encodeURIComponent(threadId)}/provide-information`,
    payload,
    { signal }
  )
}

// ---------------------------------------------------------------------------
// Case Events Audit History & Reporting (Staff RBAC)
// ---------------------------------------------------------------------------

/**
 * Retrieves read-only chronological audit history for a support case.
 */
export async function getCaseAuditEvents(
  caseIdentifier: string | number,
  signal?: AbortSignal
): Promise<CaseEventsListResponse> {
  const endpoint = typeof caseIdentifier === 'number'
    ? `/v1/cases/${encodeURIComponent(caseIdentifier)}/events`
    : `/v1/cases/by-number/${encodeURIComponent(caseIdentifier)}/events`
  return api.get<CaseEventsListResponse>(endpoint, { signal })
}

/**
 * Retrieves real-time operational metrics and category distributions for staff.
 */
export async function getAnalyticsOverview(signal?: AbortSignal): Promise<AnalyticsOverviewResponse> {
  return api.get<AnalyticsOverviewResponse>('/v1/analytics/overview', { signal })
}

// ---------------------------------------------------------------------------
// System Diagnostics
// ---------------------------------------------------------------------------

export async function getSystemStatus(signal?: AbortSignal): Promise<SystemStatusResponse> {
  return api.get<SystemStatusResponse>('/v1/status', { signal })
}

export async function getHealthProbe(signal?: AbortSignal): Promise<HealthProbeResponse> {
  return apiClient<HealthProbeResponse>('/health', { signal, method: 'GET' })
}

