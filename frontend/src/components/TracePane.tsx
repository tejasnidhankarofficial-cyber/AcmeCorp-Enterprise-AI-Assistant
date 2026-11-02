import type { AuditEntry, PendingEvent } from '../types'
import { DecisionChip } from './DecisionChip'

interface Props {
  entries: AuditEntry[]
  pending: PendingEvent | null
}

export function TracePane({ entries, pending }: Props) {
  return (
    <aside aria-label="Tool call trace" className="flex min-h-0 flex-col rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <h2 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">
        Live trace <span className="font-normal text-slate-500">(MCP tool calls)</span>
      </h2>
      <ol className="flex-1 space-y-2 overflow-y-auto p-3">
        {entries.length === 0 && !pending && (
          <li className="text-sm text-slate-500">Tool calls appear here as the assistant makes them.</li>
        )}
        {entries.map((e, i) => (
          <li key={`${e.session}-${i}`} className="rounded-lg border border-slate-200 p-2 text-sm dark:border-slate-700">
            <div className="flex items-center justify-between gap-2">
              <code className="font-medium">
                {e.server}.{e.tool}
              </code>
              <DecisionChip decision={e.decision} />
            </div>
            <pre className="mt-1 overflow-x-auto text-xs text-slate-600 dark:text-slate-400">{JSON.stringify(e.args)}</pre>
            <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
              {e.duration_ms !== null && <span>{e.duration_ms} ms</span>}
              {e.flags.map((f) => (
                <span key={f} className="rounded bg-red-100 px-1.5 py-0.5 font-medium text-red-800 dark:bg-red-950 dark:text-red-300">
                  ⚠ {f.replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          </li>
        ))}
        {pending && (
          <li className="rounded-lg border border-dashed border-amber-400 p-2 text-sm">
            <code className="font-medium">
              {pending.server}.{pending.tool}
            </code>
            <div className="text-xs text-amber-800 dark:text-amber-300">awaiting your approval…</div>
          </li>
        )}
      </ol>
    </aside>
  )
}
