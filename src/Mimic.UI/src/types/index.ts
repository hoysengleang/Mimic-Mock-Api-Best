/** Types mirroring the backend schemas in `app/schemas`. */

export const HTTP_METHODS = [
  'GET',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
  'HEAD',
  'OPTIONS',
] as const
export type HttpMethod = (typeof HTTP_METHODS)[number]

export type BodyMode = 'none' | 'json' | 'text' | 'form' | 'xml'
export type AuthType = 'none' | 'bearer' | 'basic' | 'apikey'
export type ApiKeyLocation = 'header' | 'query'

export type AssertionSource =
  | 'status'
  | 'response_time'
  | 'body'
  | 'json_path'
  | 'header'

export type AssertionOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'less_than'
  | 'greater_than'
  | 'exists'
  | 'not_exists'
  | 'is_empty'
  | 'is_not_empty'
  | 'matches'

export interface KeyValue {
  key: string
  value: string
  enabled: boolean
  description: string
}

export interface AuthConfig {
  type: AuthType
  token: string
  username: string
  password: string
  key: string
  value: string
  add_to: ApiKeyLocation
}

export interface Assertion {
  source: AssertionSource
  property: string
  operator: AssertionOperator
  target: string
  enabled: boolean
}

export interface AssertionResult {
  source: string
  property: string
  operator: string
  target: string
  actual: string
  passed: boolean
  message: string
}

export interface SavedRequest {
  id: string
  collection_id: string
  folder_id: string | null
  name: string
  description: string
  method: HttpMethod
  url: string
  headers: KeyValue[]
  query_params: KeyValue[]
  body_mode: BodyMode
  body: string
  form_data: KeyValue[]
  auth: AuthConfig
  assertions: Assertion[]
  position: number
  created_at: string
  updated_at: string
}

export interface Folder {
  id: string
  collection_id: string
  parent_id: string | null
  name: string
  position: number
  created_at: string
  updated_at: string
}

export interface Collection {
  id: string
  name: string
  description: string
  position: number
  created_at: string
  updated_at: string
}

export interface CollectionDetail extends Collection {
  folders: Folder[]
  requests: SavedRequest[]
}

export interface Variable {
  key: string
  value: string
  enabled: boolean
  secret: boolean
}

export interface Environment {
  id: string
  name: string
  is_active: boolean
  variables: Variable[]
  created_at: string
  updated_at: string
}

export interface Mock {
  id: string
  name: string
  description: string
  path: string
  method: HttpMethod
  status_code: number
  response: unknown
  response_headers: Record<string, string>
  content_type: string
  delay: number
  is_enabled: boolean
  priority: number
  hit_count: number
  last_hit_at: string | null
  created_at: string
  updated_at: string
}

export interface RedirectHop {
  url: string
  status_code: number
  location: string
}

export interface ExecuteResponse {
  ok: boolean
  error: string | null
  status_code: number | null
  status_text: string
  final_url: string
  duration_ms: number
  size_bytes: number
  headers: Record<string, string>
  body: string
  is_json: boolean
  truncated: boolean
  redirects: RedirectHop[]
  assertion_results: AssertionResult[]
  assertions_passed: number
  assertions_failed: number
  history_id: string | null
}

export interface HistoryEntry {
  id: string
  request_id: string | null
  name: string
  method: string
  url: string
  status_code: number | null
  duration_ms: number
  response_size: number
  request_headers: Record<string, string>
  request_body: string
  response_headers: Record<string, string>
  response_body: string
  truncated: boolean
  error: string | null
  assertion_results: AssertionResult[]
  created_at: string
}

export interface RunStepResult {
  iteration: number
  request_id: string
  name: string
  method: string
  url: string
  ok: boolean
  status_code: number | null
  duration_ms: number
  size_bytes: number
  error: string | null
  assertion_results: AssertionResult[]
  assertions_passed: number
  assertions_failed: number
}

export interface RunResult {
  id: string
  collection_id: string | null
  collection_name: string
  environment_id: string | null
  iterations: number
  total_requests: number
  total_assertions: number
  passed: number
  failed: number
  duration_ms: number
  status: 'passed' | 'failed'
  results: RunStepResult[]
  created_at: string
}

export interface RunSummary {
  id: string
  collection_id: string | null
  collection_name: string
  iterations: number
  total_requests: number
  total_assertions: number
  passed: number
  failed: number
  duration_ms: number
  status: 'passed' | 'failed'
  created_at: string
}

export interface Paged<T> {
  total: number
  limit: number
  offset: number
  items: T[]
}

/** An open tab in the workspace. Holds unsaved edits. */
export interface RequestTab {
  /** Local tab id — not the saved request id. */
  tabId: string
  requestId: string | null
  collectionId: string | null
  name: string
  method: HttpMethod
  url: string
  headers: KeyValue[]
  query_params: KeyValue[]
  body_mode: BodyMode
  body: string
  form_data: KeyValue[]
  auth: AuthConfig
  assertions: Assertion[]
  dirty: boolean
  sending: boolean
  response: ExecuteResponse | null
}

export function emptyKeyValue(): KeyValue {
  return { key: '', value: '', enabled: true, description: '' }
}

export function emptyAuth(): AuthConfig {
  return {
    type: 'none',
    token: '',
    username: '',
    password: '',
    key: '',
    value: '',
    add_to: 'header',
  }
}

export function emptyAssertion(): Assertion {
  return {
    source: 'status',
    property: '',
    operator: 'equals',
    target: '200',
    enabled: true,
  }
}
