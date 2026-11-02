import { useEffect, useState } from 'react'
import type { PendingEvent } from '../types'

export const APPROVAL_SECONDS = 120 // mirrors the server's fail-closed timeout

interface Props {
  pending: PendingEvent
  busy: boolean
  onDecide: (approve: boolean) => void
}

export function ApprovalCard({ pending, busy, onDecide }: Props) {
  const [left, setLeft] = useState(APPROVAL_SECONDS)

  useEffect(() => {
    const id = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000)
    return () => clearInterval(id)
  }, [])

  const expired = left === 0
  return (
    <section
      role="alertdialog"
      aria-label="Approval required"
      className="rounded-xl border-2 border-amber-400 bg-amber-50 p-4 dark:border-amber-500 dark:bg-amber-950/40"
    >
      <h3 className="font-semibold text-amber-900 dark:text-amber-200">Approval required</h3>
      <p className="mt-1 text-sm">
        The assistant wants to run a tool that changes data:{' '}
        <code className="rounded bg-amber-100 px-1 dark:bg-amber-900">
          {pending.server}.{pending.tool}
        </code>
      </p>
      <pre className="mt-2 overflow-x-auto rounded bg-white p-2 text-xs dark:bg-slate-900">
        {JSON.stringify(pending.args, null, 2)}
      </pre>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={() => onDecide(true)}
          disabled={busy || expired}
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          onClick={() => onDecide(false)}
          disabled={busy || expired}
          className="rounded-lg bg-slate-200 px-3 py-1.5 text-sm font-medium hover:bg-slate-300 disabled:opacity-50 dark:bg-slate-700 dark:hover:bg-slate-600"
        >
          Reject
        </button>
        <span className="text-xs text-slate-600 dark:text-slate-400" aria-live="off">
          {expired ? 'Expired: the action will not run' : `Auto-rejects in ${left}s`}
        </span>
      </div>
    </section>
  )
}
