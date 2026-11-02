import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const USERS = [
  { user: 'ivan', role: 'intern', servers: ['docs'], can_write: false, audit_all: false },
  { user: 'alice', role: 'employee', servers: ['docs', 'notes', 'tickets'], can_write: true, audit_all: false },
  { user: 'hana', role: 'hr', servers: ['docs', 'hr', 'notes', 'tickets'], can_write: true, audit_all: true },
]
const tool = (server: string, name: string, read_only = true) => ({ name: `${server}__${name}`, read_only, description: '' })
const TOOLS: Record<string, ReturnType<typeof tool>[]> = {
  ivan: [tool('docs', 'search_docs')],
  alice: [tool('docs', 'search_docs'), tool('tickets', 'create_ticket', false)],
  hana: [tool('docs', 'search_docs'), tool('hr', 'search_docs'), tool('tickets', 'create_ticket', false)],
}
const entry = (decision: string) => ({
  ts: '2026-11-01T10:00:00+00:00', session: 's1', user: 'alice', role: 'employee', server: 'tickets',
  tool: 'create_ticket', args: { title: 'x' }, decision, result: '', duration_ms: 2, flags: [],
})

type Handler = (url: string, init?: RequestInit) => unknown
let routes: Record<string, Handler>

function respond(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }))
}

beforeEach(() => {
  localStorage.clear()
  routes = {
    '/users': () => USERS,
    '/info': () => ({ planner: 'OfflinePlanner' }),
    '/tools': (url) => ({ role: 'x', tools: TOOLS[new URL(url, 'http://t').searchParams.get('user')!] }),
  }
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    const path = new URL(url, 'http://t').pathname
    const key = Object.keys(routes).find((k) => path === k || path.startsWith(k + '/'))
    if (!key) return respond({ detail: 'not found' }, 404)
    const out = routes[key](url, init)
    return out instanceof Response ? Promise.resolve(out) : respond(out)
  }))
})
afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('shows only the servers a role can use and updates when the user switches', async () => {
    render(<App />)
    const sidebar = await screen.findByRole('navigation', { name: /identity and tools/i })
    await waitFor(() => expect(within(sidebar).getByTestId('server-tickets')).toBeInTheDocument())
    expect(within(sidebar).queryByTestId('server-hr')).not.toBeInTheDocument()

    await userEvent.click(within(sidebar).getByRole('radio', { name: /hana/i }))
    await waitFor(() => expect(within(sidebar).getByTestId('server-hr')).toBeInTheDocument())

    await userEvent.click(within(sidebar).getByRole('radio', { name: /ivan/i }))
    await waitFor(() => expect(within(sidebar).queryByTestId('server-tickets')).not.toBeInTheDocument())
    expect(within(sidebar).getByText('search_docs')).toBeInTheDocument()
  })

  it('pauses on a side-effecting tool, then completes after the user approves', async () => {
    routes['/ask'] = () => ({
      status: 'pending_approval', run_id: 'r1', approval_id: 'a1', server: 'tickets', tool: 'create_ticket', args: { title: 'x' },
    })
    routes['/approvals'] = () => ({ status: 'done', run_id: 'r1', answer: 'Ticket 61 created.', trace: [entry('approved')] })
    render(<App />)
    await userEvent.type(await screen.findByLabelText('Message'), 'Create a ticket: x{enter}')

    expect(await screen.findByRole('alertdialog', { name: /approval required/i })).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toBeDisabled() // cannot chat past a pending approval

    await userEvent.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('Ticket 61 created.')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    const trace = screen.getByRole('complementary', { name: /tool call trace/i })
    expect(within(trace).getByText('approved')).toBeInTheDocument()
  })

  it('tells the user when an approval expired instead of failing silently', async () => {
    routes['/ask'] = () => ({ status: 'pending_approval', run_id: 'r1', approval_id: 'a1', server: 'tickets', tool: 'create_ticket', args: {} })
    routes['/approvals'] = () => new Response(JSON.stringify({ detail: 'expired' }), { status: 404, headers: { 'content-type': 'application/json' } })
    render(<App />)
    await userEvent.type(await screen.findByLabelText('Message'), 'Create a ticket: x{enter}')
    await userEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByText(/approval expired, so the action was not performed/i)).toBeInTheDocument()
  })

  it('audit tab hides the user filter from roles that can only see their own entries', async () => {
    routes['/audit'] = () => [entry('approved')]
    render(<App />)
    await screen.findByRole('radio', { name: /alice/i })
    await userEvent.click(screen.getByRole('tab', { name: 'Audit log' }))
    expect(await screen.findByText(/only see your own tool calls/i)).toBeInTheDocument()
    expect(screen.queryByLabelText('Filter by user')).not.toBeInTheDocument()
    expect(await screen.findByText('tickets.create_ticket')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Assistant' }))
    await userEvent.click(await screen.findByRole('radio', { name: /hana/i }))
    await userEvent.click(screen.getByRole('tab', { name: 'Audit log' }))
    expect(await screen.findByLabelText('Filter by user')).toBeInTheDocument()
  })
})
