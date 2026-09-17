import type { ReactNode } from 'react'

/**
 * A system message: a fetch failed, a list is empty, a submit was refused. Set in
 * ink on a quiet ground, never in Seal Vermilion — that colour means a package
 * fails a rule, and a dropped connection says nothing about a package.
 */
export function Notice({
  title,
  children,
  action,
  role,
}: {
  title: string
  children?: ReactNode
  action?: ReactNode
  role?: 'alert' | 'status'
}) {
  return (
    <div role={role} className="card flex flex-col items-start gap-3 border-dashed p-5 shadow-none sm:p-6">
      <div>
        <p className="text-body font-semibold text-ink">{title}</p>
        {children && <div className="mt-1 text-secondary text-mute">{children}</div>}
      </div>
      {action}
    </div>
  )
}
