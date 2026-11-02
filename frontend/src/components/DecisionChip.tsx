import type { Decision } from '../types'

const STYLES: Record<Decision, string> = {
  allowed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  approved: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  denied_role: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
  denied_user: 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300',
  error: 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
}

// The label is always spelled out, so meaning never depends on colour alone.
export function DecisionChip({ decision }: { decision: Decision }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[decision] ?? STYLES.error}`}>
      {decision.replace('_', ' ')}
    </span>
  )
}
