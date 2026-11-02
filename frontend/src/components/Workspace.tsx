import { useState } from 'react'
import { api, ApiError } from '../api'
import type { AuditEntry, PendingEvent, RunEvent } from '../types'
import { Chat, type Message } from './Chat'
import { TracePane } from './TracePane'

const SUGGESTIONS = [
  'What is our remote work policy?',
  'Any tickets about VPN issues?',
  'Create a ticket: monitor flickering',
  'What is the salary band?',
  'Tell me about the analytics vendor',
]

/** One chat session for one user. App remounts it (via key) when the user changes, resetting all state. */
export function Workspace({ user }: { user: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [trace, setTrace] = useState<AuditEntry[]>([])
  const [pending, setPending] = useState<PendingEvent | null>(null)
  const [busy, setBusy] = useState(false)

  const say = (role: Message['role'], text: string) => setMessages((m) => [...m, { role, text }])

  const handle = (event: RunEvent) => {
    if (event.status === 'pending_approval') {
      setPending(event)
      return
    }
    setPending(null)
    if (event.status === 'done') {
      setTrace((t) => [...t, ...event.trace])
      say('assistant', event.answer)
    } else {
      say('system', `Something went wrong: ${event.detail}`)
    }
  }

  const run = async (call: () => Promise<RunEvent>) => {
    setBusy(true)
    try {
      handle(await call())
    } catch (err) {
      setPending(null)
      if (err instanceof ApiError && err.status === 404) {
        say('system', 'That approval expired, so the action was not performed. Ask again if you still want it.')
      } else {
        say('system', err instanceof Error ? err.message : 'Request failed')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Chat
        messages={messages}
        pending={pending}
        busy={busy}
        suggestions={SUGGESTIONS}
        onSend={(q) => {
          say('user', q)
          void run(() => api.ask(user, q))
        }}
        onDecide={(approve) => {
          if (!pending) return
          say('system', approve ? 'You approved the action.' : 'You rejected the action.')
          void run(() => api.decide(pending.approval_id, user, approve))
        }}
      />
      <TracePane entries={trace} pending={pending} />
    </>
  )
}
