import { useEffect, useRef, useState } from 'react'
import { ApprovalCard } from './ApprovalCard'
import type { PendingEvent } from '../types'

export interface Message {
  role: 'user' | 'assistant' | 'system'
  text: string
}

interface Props {
  messages: Message[]
  pending: PendingEvent | null
  busy: boolean
  onSend: (text: string) => void
  onDecide: (approve: boolean) => void
  suggestions: string[]
}

export function Chat({ messages, pending, busy, onSend, onDecide, suggestions }: Props) {
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const locked = busy || pending !== null // no new questions while a run is working or awaiting approval

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages, pending, busy])

  const submit = (text: string) => {
    const q = text.trim()
    if (!q || locked) return
    setDraft('')
    onSend(q)
  }

  return (
    <section aria-label="Chat" className="flex min-h-[420px] min-w-0 flex-col rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Ask about company policies, tickets or notes. Try one of these, then switch user to see how access changes:
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex'}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-2 text-sm ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : m.role === 'system'
                    ? 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200'
                    : 'bg-slate-100 dark:bg-slate-800'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {pending && <ApprovalCard key={pending.approval_id} pending={pending} busy={busy} onDecide={onDecide} />}
        {busy && !pending && <p className="text-sm text-slate-500">Working…</p>}
        <div ref={endRef} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit(draft)
        }}
        className="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800"
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={pending ? 'Answer the approval request first…' : 'Ask the assistant…'}
          aria-label="Message"
          disabled={locked}
          className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 text-sm disabled:opacity-60 dark:border-slate-700"
        />
        <button
          type="submit"
          disabled={locked || !draft.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  )
}
