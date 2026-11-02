import { Fragment, useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { AuditEntry, User } from '../types'
import { DecisionChip } from './DecisionChip'

const SERVERS = ['docs', 'hr', 'notes', 'tickets']
const DECISIONS = ['allowed', 'approved', 'denied_role', 'denied_user', 'error']

export function AuditTab({ viewer, users }: { viewer: User; users: User[] }) {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState('')
  const [server, setServer] = useState('')
  const [decision, setDecision] = useState('')
  const [flaggedOnly, setFlaggedOnly] = useState(false)
  const [open, setOpen] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setEntries(await api.audit(viewer.user, { user, server, decision, flagged: flaggedOnly || undefined }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit log')
    } finally {
      setLoading(false)
    }
  }, [viewer.user, user, server, decision, flaggedOnly])

  useEffect(() => {
    void load()
  }, [load])

  const select = 'rounded-lg border border-slate-300 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900'
  return (
    <section aria-label="Audit log" className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {viewer.audit_all
          ? `As ${viewer.role} you can see every user's tool calls.`
          : `As ${viewer.role} you can only see your own tool calls.`}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {viewer.audit_all && (
          <select aria-label="Filter by user" value={user} onChange={(e) => setUser(e.target.value)} className={select}>
            <option value="">All users</option>
            {users.map((u) => (
              <option key={u.user}>{u.user}</option>
            ))}
          </select>
        )}
        <select aria-label="Filter by server" value={server} onChange={(e) => setServer(e.target.value)} className={select}>
          <option value="">All servers</option>
          {SERVERS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select aria-label="Filter by decision" value={decision} onChange={(e) => setDecision(e.target.value)} className={select}>
          <option value="">All decisions</option>
          {DECISIONS.map((d) => (
            <option key={d}>{d}</option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={flaggedOnly} onChange={(e) => setFlaggedOnly(e.target.checked)} />
          Flagged only
        </label>
        <button onClick={() => void load()} className="ml-auto rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
          Refresh
        </button>
      </div>

      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500 dark:border-slate-800">
            <tr>
              {['Time', 'User', 'Tool', 'Decision', 'Flags'].map((h) => (
                <th key={h} className="px-3 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!loading && entries.length === 0 && (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No matching audit entries.</td></tr>
            )}
            {entries.map((e, i) => (
              <Fragment key={`${e.session}-${e.ts}-${i}`}>
                <tr onClick={() => setOpen(open === i ? null : i)} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                  <td className="whitespace-nowrap px-3 py-2 text-xs">{e.ts.replace('T', ' ').slice(0, 19)}</td>
                  <td className="px-3 py-2">{e.user} <span className="text-xs text-slate-500">({e.role})</span></td>
                  <td className="px-3 py-2 font-mono text-xs">{e.server}.{e.tool}</td>
                  <td className="px-3 py-2"><DecisionChip decision={e.decision} /></td>
                  <td className="px-3 py-2 text-xs">{e.flags.length ? `⚠ ${e.flags.join(', ').replaceAll('_', ' ')}` : '—'}</td>
                </tr>
                {open === i && (
                  <tr className="border-b border-slate-100 dark:border-slate-800">
                    <td colSpan={5} className="bg-slate-50 px-3 py-2 dark:bg-slate-950">
                      <pre className="overflow-x-auto text-xs">{JSON.stringify(e, null, 2)}</pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
