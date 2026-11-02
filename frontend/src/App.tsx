import { useEffect, useState } from 'react'
import { api } from './api'
import { AuditTab } from './components/AuditTab'
import { Sidebar } from './components/Sidebar'
import { Workspace } from './components/Workspace'
import type { Tool, User } from './types'

type Tab = 'assistant' | 'audit'
const STORED_USER = 'acme.user'

function readStoredUser(): string | null {
  try {
    return localStorage.getItem(STORED_USER)
  } catch {
    return null // storage can be blocked; the UI works without it
  }
}

export default function App() {
  const [users, setUsers] = useState<User[]>([])
  const [user, setUser] = useState<string>('')
  const [tab, setTab] = useState<Tab>('assistant')
  const [tools, setTools] = useState<Tool[]>([])
  const [loadingTools, setLoadingTools] = useState(false)
  const [planner, setPlanner] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.users().then((list) => {
      setUsers(list)
      const stored = readStoredUser()
      setUser(list.find((u) => u.user === stored)?.user ?? list.find((u) => u.user === 'alice')?.user ?? list[0]?.user ?? '')
    }).catch(() => setError('Cannot reach the API. Is the server running on port 8000?'))
    api.info().then((i) => setPlanner(i.planner)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    setLoadingTools(true)
    api.tools(user)
      .then((r) => !cancelled && setTools(r.tools))
      .catch(() => !cancelled && setTools([]))
      .finally(() => !cancelled && setLoadingTools(false))
    return () => {
      cancelled = true
    }
  }, [user])

  const select = (name: string) => {
    setUser(name)
    try {
      localStorage.setItem(STORED_USER, name)
    } catch {
      /* ignore */
    }
  }

  const current = users.find((u) => u.user === user)
  const tabButton = (id: Tab, label: string) => (
    <button
      role="tab"
      aria-selected={tab === id}
      onClick={() => setTab(id)}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium ${tab === id ? 'bg-indigo-600 text-white' : 'hover:bg-slate-200 dark:hover:bg-slate-800'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-4 p-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Acme Knowledge Assistant</h1>
          <p className="text-xs text-slate-500">Model Context Protocol · role-scoped tools · human approval · audit trail</p>
        </div>
        <div className="flex items-center gap-3">
          {planner && (
            <span className="rounded-full border border-slate-300 px-2.5 py-1 text-xs dark:border-slate-700" title="LLM backend in use">
              {planner}
            </span>
          )}
          <div role="tablist" className="flex gap-1">
            {tabButton('assistant', 'Assistant')}
            {tabButton('audit', 'Audit log')}
          </div>
        </div>
      </header>

      {error && <p role="alert" className="rounded-lg bg-red-100 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-300">{error}</p>}

      {current && tab === 'assistant' && (
        <main className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[240px_minmax(0,1fr)_340px]">
          <Sidebar users={users} current={user} onSelect={select} tools={tools} loadingTools={loadingTools} />
          <Workspace key={user} user={user} />
        </main>
      )}
      {current && tab === 'audit' && <AuditTab key={user} viewer={current} users={users} />}
    </div>
  )
}
