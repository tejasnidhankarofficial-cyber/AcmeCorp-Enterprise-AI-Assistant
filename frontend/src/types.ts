export interface User {
  user: string
  role: string
  servers: string[]
  can_write: boolean
  audit_all: boolean
}

export interface Tool {
  name: string // namespaced: server__tool
  read_only: boolean
  description: string
}

export type Decision = 'allowed' | 'approved' | 'denied_role' | 'denied_user' | 'error'

export interface AuditEntry {
  ts: string
  session: string
  user: string
  role: string
  server: string
  tool: string
  args: Record<string, unknown>
  decision: Decision
  result: string
  duration_ms: number | null
  flags: string[]
}

export interface PendingEvent {
  status: 'pending_approval'
  run_id: string
  approval_id: string
  server: string
  tool: string
  args: Record<string, unknown>
}
export interface DoneEvent {
  status: 'done'
  run_id: string
  answer: string
  trace: AuditEntry[]
}
export interface ErrorEvent {
  status: 'error'
  run_id: string
  detail: string
}
export type RunEvent = PendingEvent | DoneEvent | ErrorEvent

export interface AuditFilters {
  user?: string
  server?: string
  decision?: string
  flagged?: boolean
}
