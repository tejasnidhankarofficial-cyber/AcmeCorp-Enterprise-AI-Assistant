import type { AuditEntry, AuditFilters, RunEvent, Tool, User } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { 'content-type': 'application/json' }, ...init })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = String((await res.json()).detail ?? detail)
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const qs = (params: Record<string, string | boolean | undefined>) => {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') search.set(k, String(v))
  return search.toString()
}

export const api = {
  users: () => request<User[]>('/users'),
  info: () => request<{ planner: string }>('/info'),
  tools: (user: string) => request<{ role: string; tools: Tool[] }>(`/tools?${qs({ user })}`),
  ask: (user: string, question: string) =>
    request<RunEvent>('/ask', { method: 'POST', body: JSON.stringify({ user, question, interactive: true }) }),
  decide: (approvalId: string, user: string, approve: boolean) =>
    request<RunEvent>(`/approvals/${approvalId}`, { method: 'POST', body: JSON.stringify({ user, approve }) }),
  audit: (viewer: string, filters: AuditFilters = {}) =>
    request<AuditEntry[]>(`/audit?${qs({ viewer, ...filters })}`),
}
