import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { APPROVAL_SECONDS, ApprovalCard } from './ApprovalCard'
import type { PendingEvent } from '../types'

const pending: PendingEvent = {
  status: 'pending_approval', run_id: 'r1', approval_id: 'a1',
  server: 'tickets', tool: 'create_ticket', args: { title: 'Broken keyboard' },
}

afterEach(() => vi.useRealTimers())

describe('ApprovalCard', () => {
  it('shows the tool and its arguments and reports the decision', async () => {
    const onDecide = vi.fn()
    render(<ApprovalCard pending={pending} busy={false} onDecide={onDecide} />)
    expect(screen.getByText('tickets.create_ticket')).toBeInTheDocument()
    expect(screen.getByText(/Broken keyboard/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Approve' }))
    await userEvent.click(screen.getByRole('button', { name: 'Reject' }))
    expect(onDecide.mock.calls).toEqual([[true], [false]])
  })

  it('disables both buttons once the server-side timeout has elapsed', () => {
    vi.useFakeTimers()
    render(<ApprovalCard pending={pending} busy={false} onDecide={vi.fn()} />)
    act(() => { vi.advanceTimersByTime(APPROVAL_SECONDS * 1000) })
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeDisabled()
    expect(screen.getByText(/will not run/)).toBeInTheDocument()
  })
})
