/**
 * Typed client for the Mimic API.
 *
 * Requests go to a relative `/api` path, which Vite proxies to the backend in
 * development and which is same-origin in production. That keeps CORS out of
 * the picture entirely rather than relying on a permissive policy.
 */

import type {
  Collection,
  CollectionDetail,
  Environment,
  ExecuteResponse,
  Folder,
  HistoryEntry,
  Mock,
  Paged,
  RunResult,
  RunSummary,
  SavedRequest,
} from '@/types'

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

/** An error carrying the backend's structured detail, for inline display. */
export class ApiError extends Error {
  readonly status: number
  readonly problems: Array<{ field: string; message: string }>

  constructor(
    message: string,
    status: number,
    problems: Array<{ field: string; message: string }> = [],
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problems = problems
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...init.headers,
      },
    })
  } catch {
    throw new ApiError(
      'Cannot reach the Mimic server. Is the backend running?',
      0,
    )
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = text
    }
  }

  if (!response.ok) {
    const body = payload as
      | { detail?: string; problems?: Array<{ field: string; message: string }> }
      | string
      | null

    const detail =
      typeof body === 'string'
        ? body
        : (body?.detail ?? `Request failed with status ${response.status}`)

    throw new ApiError(
      detail,
      response.status,
      typeof body === 'object' && body ? (body.problems ?? []) : [],
    )
  }

  return payload as T
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) })

export const api = {
  // --- Health -------------------------------------------------------------
  health: () => request<{ status: string }>('/health'),
  ready: () =>
    request<{
      status: string
      database: string
      version: string
      counts: Record<string, number>
    }>('/health/ready'),

  // --- Collections --------------------------------------------------------
  /** Returns every collection with its folders and requests, in one call. */
  listCollections: () => request<CollectionDetail[]>('/collections'),

  getCollection: (id: string) =>
    request<CollectionDetail>(`/collections/${id}`),

  createCollection: (body: { name: string; description?: string }) =>
    request<Collection>('/collections', { method: 'POST', ...json(body) }),

  updateCollection: (id: string, body: Partial<Collection>) =>
    request<Collection>(`/collections/${id}`, { method: 'PATCH', ...json(body) }),

  deleteCollection: (id: string) =>
    request<void>(`/collections/${id}`, { method: 'DELETE' }),

  // --- Folders ------------------------------------------------------------
  createFolder: (
    collectionId: string,
    body: { name: string; parent_id?: string | null },
  ) =>
    request<Folder>(`/collections/${collectionId}/folders`, {
      method: 'POST',
      ...json(body),
    }),

  updateFolder: (id: string, body: Partial<Folder>) =>
    request<Folder>(`/folders/${id}`, { method: 'PATCH', ...json(body) }),

  deleteFolder: (id: string) =>
    request<void>(`/folders/${id}`, { method: 'DELETE' }),

  // --- Requests -----------------------------------------------------------
  createRequest: (collectionId: string, body: Partial<SavedRequest>) =>
    request<SavedRequest>(`/collections/${collectionId}/requests`, {
      method: 'POST',
      ...json(body),
    }),

  getRequest: (id: string) => request<SavedRequest>(`/requests/${id}`),

  updateRequest: (id: string, body: Partial<SavedRequest>) =>
    request<SavedRequest>(`/requests/${id}`, { method: 'PATCH', ...json(body) }),

  deleteRequest: (id: string) =>
    request<void>(`/requests/${id}`, { method: 'DELETE' }),

  duplicateRequest: (id: string) =>
    request<SavedRequest>(`/requests/${id}/duplicate`, { method: 'POST' }),

  // --- Environments -------------------------------------------------------
  listEnvironments: () => request<Environment[]>('/environments'),

  createEnvironment: (body: Partial<Environment>) =>
    request<Environment>('/environments', { method: 'POST', ...json(body) }),

  updateEnvironment: (id: string, body: Partial<Environment>) =>
    request<Environment>(`/environments/${id}`, {
      method: 'PATCH',
      ...json(body),
    }),

  activateEnvironment: (id: string) =>
    request<Environment>(`/environments/${id}/activate`, { method: 'POST' }),

  deactivateAllEnvironments: () =>
    request<void>('/environments/deactivate-all', { method: 'POST' }),

  deleteEnvironment: (id: string) =>
    request<void>(`/environments/${id}`, { method: 'DELETE' }),

  // --- Mocks --------------------------------------------------------------
  listMocks: (search = '') =>
    request<Mock[]>(
      `/mocks${search ? `?search=${encodeURIComponent(search)}` : ''}`,
    ),

  createMock: (body: Partial<Mock>) =>
    request<Mock>('/mocks', { method: 'POST', ...json(body) }),

  updateMock: (id: string, body: Partial<Mock>) =>
    request<Mock>(`/mocks/${id}`, { method: 'PATCH', ...json(body) }),

  deleteMock: (id: string) => request<void>(`/mocks/${id}`, { method: 'DELETE' }),

  toggleMock: (id: string) =>
    request<Mock>(`/mocks/${id}/toggle`, { method: 'POST' }),

  resetMockHits: () => request<void>('/mocks/reset-hits', { method: 'POST' }),

  // --- Execution ----------------------------------------------------------
  send: (body: Record<string, unknown>) =>
    request<ExecuteResponse>('/send', { method: 'POST', ...json(body) }),

  listHistory: (limit = 50, offset = 0) =>
    request<Paged<HistoryEntry>>(`/history?limit=${limit}&offset=${offset}`),

  deleteHistoryEntry: (id: string) =>
    request<void>(`/history/${id}`, { method: 'DELETE' }),

  clearHistory: () => request<void>('/history', { method: 'DELETE' }),

  // --- Runner -------------------------------------------------------------
  run: (body: {
    collection_id: string
    environment_id?: string | null
    iterations?: number
    delay_ms?: number
    stop_on_failure?: boolean
  }) => request<RunResult>('/run', { method: 'POST', ...json(body) }),

  listRuns: (limit = 25) => request<Paged<RunSummary>>(`/runs?limit=${limit}`),

  getRun: (id: string) => request<RunResult>(`/runs/${id}`),

  clearRuns: () => request<void>('/runs', { method: 'DELETE' }),
}
