import type { Tool, User } from '../types'

interface Props {
  users: User[]
  current: string
  onSelect: (user: string) => void
  tools: Tool[]
  loadingTools: boolean
}

const ROLE_STYLE: Record<string, string> = {
  intern: 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200',
  employee: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300',
  manager: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300',
  hr: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300',
}

export function Sidebar({ users, current, onSelect, tools, loadingTools }: Props) {
  const byServer = new Map<string, Tool[]>()
  for (const t of tools) {
    const server = t.name.split('__')[0]
    byServer.set(server, [...(byServer.get(server) ?? []), t])
  }

  return (
    <nav aria-label="Identity and tools" className="space-y-4">
      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Signed in as</h2>
        <div role="radiogroup" aria-label="Demo user" className="space-y-1">
          {users.map((u) => (
            <button
              key={u.user}
              role="radio"
              aria-checked={u.user === current}
              onClick={() => onSelect(u.user)}
              className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm ${
                u.user === current
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40'
                  : 'border-slate-200 bg-white hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800'
              }`}
            >
              <span className="font-medium capitalize">{u.user}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${ROLE_STYLE[u.role] ?? ROLE_STYLE.intern}`}>{u.role}</span>
            </button>
          ))}
        </div>
      </section>

      <section aria-label="Discovered tools">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Discovered tools {loadingTools ? '' : `(${tools.length})`}
        </h2>
        {loadingTools ? (
          <p className="text-sm text-slate-500">Connecting to MCP servers…</p>
        ) : (
          <div className="space-y-3">
            {[...byServer].map(([server, list]) => (
              <div key={server} data-testid={`server-${server}`}>
                <div className="text-sm font-medium">{server}</div>
                <ul className="mt-1 space-y-0.5">
                  {list.map((t) => (
                    <li key={t.name} className="flex items-center justify-between text-xs">
                      <span className="font-mono">{t.name.split('__')[1]}</span>
                      <span className={t.read_only ? 'text-emerald-700 dark:text-emerald-400' : 'font-semibold text-amber-700 dark:text-amber-400'}>
                        {t.read_only ? 'read-only' : 'side-effect'}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>
    </nav>
  )
}
