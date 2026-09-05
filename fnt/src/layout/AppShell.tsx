import type { ReactNode } from 'react'

interface AppShellProps {
  surfaceLabel: string
  children: ReactNode
}

/**
 * Shared chrome for both surfaces. Takes children instead of an <Outlet />
 * so /officer and /admin each mount it explicitly inside their own route
 * tree — this file must never import from either surface.
 */
export function AppShell({ surfaceLabel, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <span className="text-sm font-semibold tracking-wide">PCCS</span>
        <span className="ml-2 text-sm text-slate-500">{surfaceLabel}</span>
      </header>
      <main className="p-4">{children}</main>
    </div>
  )
}
