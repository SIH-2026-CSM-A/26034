import { Link, useLocation } from 'react-router-dom'

interface OfficerHeaderProps {
  currentTitle?: string
}

export function OfficerHeader({ currentTitle }: OfficerHeaderProps) {
  const location = useLocation()
  const path = location.pathname

  const isQueue = path.includes('/officer/queue')
  const isDashboard = path.includes('/officer/dashboard')
  const isVendors = path.includes('/officer/vendors')
  const isComplaints = path.includes('/officer/complaints')

  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-y-2 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
          <span className="text-label font-bold tracking-wider text-ink">PCCS</span>
          {currentTitle && (
            <span className="hidden font-mono text-label text-mute sm:inline">
              / {currentTitle}
            </span>
          )}
          <nav aria-label="Officer primary navigation" className="flex items-center gap-1 sm:gap-2">
            <Link
              to="/officer/queue"
              className={`flex min-h-target items-center px-2 py-1 text-label transition-colors sm:px-3 ${
                isQueue
                  ? 'border-b-2 border-ink font-semibold text-ink'
                  : 'text-mute hover:text-ink'
              }`}
            >
              Queue
            </Link>
            <Link
              to="/officer/dashboard"
              className={`flex min-h-target items-center px-2 py-1 text-label transition-colors sm:px-3 ${
                isDashboard
                  ? 'border-b-2 border-ink font-semibold text-ink'
                  : 'text-mute hover:text-ink'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/officer/vendors"
              className={`flex min-h-target items-center px-2 py-1 text-label transition-colors sm:px-3 ${
                isVendors
                  ? 'border-b-2 border-ink font-semibold text-ink'
                  : 'text-mute hover:text-ink'
              }`}
            >
              Vendor Submissions
            </Link>
            <Link
              to="/officer/complaints"
              className={`flex min-h-target items-center px-2 py-1 text-label transition-colors sm:px-3 ${
                isComplaints
                  ? 'border-b-2 border-ink font-semibold text-ink'
                  : 'text-mute hover:text-ink'
              }`}
            >
              Complaints
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            to="/officer/capture"
            className="flex min-h-target items-center border border-ink bg-paper px-3 py-1 font-mono text-label text-ink hover:bg-mute/10 active:bg-mute/20"
          >
            Camera
          </Link>
          <Link
            to="/officer/new"
            className="flex min-h-target items-center border border-ink bg-ink px-3 py-1 text-label text-paper hover:bg-ink/90"
          >
            + New scan
          </Link>
        </div>
      </div>
    </header>
  )
}
