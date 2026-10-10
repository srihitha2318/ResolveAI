/**
 * Standard typed API Error containing status code and response payload
 */
export class ApiError extends Error {
  public status: number
  public data?: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
    Object.setPrototypeOf(this, ApiError.prototype)
  }
}

/**
 * Standard Options for API fetch calls
 */
export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | undefined | null>
  body?: unknown
}

/**
 * Health / Subsystem status response schema (from GET /api/v1/status)
 */
export interface SystemStatusResponse {
  app_name: string
  version?: string
  environment?: string
  database: string
  message?: string
  timestamp?: string
}

/**
 * Simple health probe response schema (from GET /health)
 */
export interface HealthProbeResponse {
  status: string
}
