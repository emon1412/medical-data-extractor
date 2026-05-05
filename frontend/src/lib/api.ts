import type {
  ActivityLogListResponse,
  ApiError,
  ExtractionResponse,
  Order,
  OrderCreate,
  OrderListResponse,
  OrderUpdate,
  Patient,
  PatientListResponse,
} from "../types/api"

const STORAGE_KEY_API = "hde.apiBaseUrl"
const STORAGE_KEY_KEY = "hde.apiKey"

// Build-time defaults from Vite env vars (`frontend/.env.local` for local dev,
// or `--build-arg VITE_API_BASE_URL=... VITE_API_KEY=...` baked into the
// production container image). Anything saved via the Settings UI takes
// precedence over these.
const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ""
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY ?? ""

export function getApiBaseUrl(): string {
  const stored = localStorage.getItem(STORAGE_KEY_API)
  if (stored !== null) return stored
  // Default: same origin (used when something proxies /api to the backend)
  return DEFAULT_API_BASE_URL
}

export function setApiBaseUrl(url: string): void {
  if (url) localStorage.setItem(STORAGE_KEY_API, url)
  else localStorage.removeItem(STORAGE_KEY_API)
}

export function getApiKey(): string {
  const stored = localStorage.getItem(STORAGE_KEY_KEY)
  if (stored !== null) return stored
  return DEFAULT_API_KEY
}

export function setApiKey(key: string): void {
  if (key) localStorage.setItem(STORAGE_KEY_KEY, key)
  else localStorage.removeItem(STORAGE_KEY_KEY)
}

function buildUrl(path: string): string {
  const base = getApiBaseUrl().replace(/\/$/, "")
  return `${base}${path}`
}

function authHeaders(): Record<string, string> {
  const k = getApiKey()
  return k ? { "X-API-Key": k } : {}
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T

  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    const apiErr = body as ApiError | string | null
    let message = `Request failed with status ${res.status}`
    if (apiErr && typeof apiErr === "object" && "error" in apiErr) {
      message = apiErr.error.message
    } else if (typeof apiErr === "string" && apiErr) {
      message = apiErr
    }
    throw new Error(message)
  }

  return body as T
}

export const api = {
  // Orders
  listOrders: (
    params: {
      limit?: number
      offset?: number
      search?: string
      status?: string
    } = {},
  ) => {
    const qs = new URLSearchParams()
    if (params.limit) qs.set("limit", String(params.limit))
    if (params.offset) qs.set("offset", String(params.offset))
    if (params.search) qs.set("search", params.search)
    if (params.status) qs.set("status", params.status)
    return fetch(buildUrl(`/api/v1/orders?${qs}`), {
      headers: authHeaders(),
    }).then(handle<OrderListResponse>)
  },

  getOrder: (id: string) =>
    fetch(buildUrl(`/api/v1/orders/${id}`), { headers: authHeaders() }).then(
      handle<Order>,
    ),

  createOrder: (payload: OrderCreate) =>
    fetch(buildUrl("/api/v1/orders"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    }).then(handle<Order>),

  updateOrder: (id: string, payload: OrderUpdate) =>
    fetch(buildUrl(`/api/v1/orders/${id}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    }).then(handle<Order>),

  deleteOrder: (id: string) =>
    fetch(buildUrl(`/api/v1/orders/${id}`), {
      method: "DELETE",
      headers: authHeaders(),
    }).then(handle<void>),

  // Extractions
  extractPdf: (file: File, createOrder: boolean) => {
    const fd = new FormData()
    fd.append("file", file)
    fd.append("create_order", String(createOrder))
    return fetch(buildUrl("/api/v1/extractions/pdf"), {
      method: "POST",
      headers: authHeaders(),
      body: fd,
    }).then(handle<ExtractionResponse>)
  },

  // Patients
  listPatients: (
    params: { limit?: number; offset?: number; search?: string } = {},
  ) => {
    const qs = new URLSearchParams()
    if (params.limit) qs.set("limit", String(params.limit))
    if (params.offset) qs.set("offset", String(params.offset))
    if (params.search) qs.set("search", params.search)
    return fetch(buildUrl(`/api/v1/patients?${qs}`), {
      headers: authHeaders(),
    }).then(handle<PatientListResponse>)
  },

  getPatient: (id: string) =>
    fetch(buildUrl(`/api/v1/patients/${id}`), { headers: authHeaders() }).then(
      handle<Patient>,
    ),

  listPatientOrders: (id: string) =>
    fetch(buildUrl(`/api/v1/patients/${id}/orders`), {
      headers: authHeaders(),
    }).then(handle<OrderListResponse>),

  // Activity logs
  listActivityLogs: (
    params: { limit?: number; offset?: number; pathContains?: string } = {},
  ) => {
    const qs = new URLSearchParams()
    if (params.limit) qs.set("limit", String(params.limit))
    if (params.offset) qs.set("offset", String(params.offset))
    if (params.pathContains) qs.set("path_contains", params.pathContains)
    return fetch(buildUrl(`/api/v1/activity-logs?${qs}`), {
      headers: authHeaders(),
    }).then(handle<ActivityLogListResponse>)
  },

  // Health
  health: () =>
    fetch(buildUrl("/api/v1/health")).then(
      handle<{ status: string; app: string; version: string }>,
    ),
}
