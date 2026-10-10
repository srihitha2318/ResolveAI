import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient, api } from '../services/api'
import { ApiError } from '../types/api'

describe('API Client Foundation', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('handles successful JSON responses', async () => {
    const mockData = { status: 'ok', app_name: 'ResolveAI' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockData,
    } as Response)

    const result = await api.get<{ status: string; app_name: string }>('/v1/status')
    expect(result).toEqual(mockData)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/status',
      expect.objectContaining({ method: 'GET' })
    )
  })

  it('handles non-2xx HTTP responses and throws typed ApiError', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Complaint thread not found' }),
    } as Response)

    await expect(apiClient('/v1/workflows/unknown-id')).rejects.toThrowError(ApiError)

    try {
      await apiClient('/v1/workflows/unknown-id')
    } catch (err) {
      const apiErr = err as ApiError
      expect(apiErr.status).toBe(404)
      expect(apiErr.message).toBe('Complaint thread not found')
    }
  })

  it('handles network connection failures gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'))

    await expect(apiClient('/v1/status')).rejects.toThrowError(ApiError)

    try {
      await apiClient('/v1/status')
    } catch (err) {
      const apiErr = err as ApiError
      expect(apiErr.status).toBe(0)
      expect(apiErr.message).toContain('Unable to connect to the ResolveAI service')
    }
  })

  it('supports query parameters serialization', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ items: [] }),
    } as Response)

    await api.get('/v1/workflows/pending-approvals', {
      params: { limit: 10, offset: 0 },
    })

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/workflows/pending-approvals?limit=10&offset=0',
      expect.anything()
    )
  })
})
