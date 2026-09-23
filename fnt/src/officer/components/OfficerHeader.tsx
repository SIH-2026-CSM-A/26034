import { motion } from 'framer-motion'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LOGIN_PATH, clearToken } from '../../services/auth'
import { Logo } from '../../ui/Logo'
import { spring } from '../../ui/motion'
import { ThemeToggle } from '../../ui/ThemeToggle'

interface OfficerHeaderProps {
  /** Kept for callers; every page already carries its title as an h1 directly below. */
  currentTitle?: string
}

const NAV: ReadonlyArray<{ to: string; label: string; short: string; icon: string }> = [
  { to: '/officer/queue', label: 'Queue', short: 'Queue', icon: 'M4 6h12M4 10h12M4 14h8' },
  {
    to: '/officer/dashboard',
    label: 'Dashboard',
    short: 'Map',
    icon: 'M3 5.5 7.5 4l5 1.5L17 4v10.5L12.5 16l-5-1.5L3 16V5.5ZM7.5 4v10.5M12.5 5.5V16',
  },
  {
    to: '/officer/vendors',
    label: 'Vendor submissions',
    short: 'Vendors',
    icon: 'M3.5 8 5 4h10l1.5 4M3.5 8v8h13V8M3.5 8h13M8 16v-4h4v4',
  },
  {
    to: '/officer/complaints',
    label: 'Complaints',
    short: 'Complaints',
    icon: 'M4 4.5h12v9H9l-3.5 3v-3H4v-9Z',
  },
]

/**
 * Officer chrome. A glass bar the page scrolls under, and on a phone a floating
 * tab bar within thumb reach — the inspector is standing up, holding a package in
 * the other hand. The active marker is one shared element that slides between
 * destinations rather than four that blink on and off.
 */
export function OfficerHeader(_props: OfficerHeaderProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  return (
    <>
      <header className="glass sticky top-0 z-30 border-b border-hairline/60">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-3 px-4 py-1.5">
          <div className="flex min-w-0 items-center gap-5">
            <Link to="/officer/queue" className="flex min-h-target shrink-0 items-center gap-2.5">
              <Logo />
              <span className="font-display text-body font-semibold tracking-tight">ClauseCam</span>
            </Link>
            <nav aria-label="Officer primary navigation" className="hidden items-center gap-1 md:flex">
              {NAV.map((item) => {
                const active = pathname.startsWith(item.to)
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    aria-current={active ? 'page' : undefined}
                    className={`relative flex min-h-target items-center px-3.5 text-secondary transition-colors duration-base ${
                      active ? 'font-medium text-ink' : 'text-mute hover:text-ink'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-pill"
                        transition={spring.snap}
                        className="absolute inset-x-0 inset-y-1.5 -z-10 rounded-full bg-ink/[0.07]"
                      />
                    )}
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2.5">
            <ThemeToggle />
            <Link to="/officer/capture" className="btn btn-quiet hidden px-4 sm:inline-flex">
              Camera
            </Link>
            <Link to="/officer/new" className="btn btn-primary px-4">
              <svg viewBox="0 0 16 16" aria-hidden="true" className="h-3.5 w-3.5" fill="none">
                <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
              New scan
            </Link>
            <button
              type="button"
              onClick={() => {
                clearToken()
                navigate(LOGIN_PATH, { replace: true })
              }}
              className="btn btn-ghost px-3 text-label text-mute"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <nav
        aria-label="Officer primary navigation"
        className="glass fixed inset-x-3 bottom-3 z-30 flex items-stretch justify-between rounded-sheet border border-hairline/60 p-1.5 shadow-e3 md:hidden"
        style={{ marginBottom: 'env(safe-area-inset-bottom)' }}
      >
        {[...NAV, { to: '/officer/capture', label: 'Camera', short: 'Camera', icon: 'M3 7h3l1.5-2h5L14 7h3v9H3V7Zm7 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z' }].map(
          (item) => {
            const active = pathname.startsWith(item.to)
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? 'page' : undefined}
                aria-label={item.label}
                className={`relative flex min-h-target min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-[22px] text-[11px] font-medium ${
                  active ? 'text-ink' : 'text-mute'
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="tab-pill"
                    transition={spring.snap}
                    className="absolute inset-0 -z-10 rounded-[22px] bg-ink/[0.08]"
                  />
                )}
                <svg viewBox="0 0 20 20" aria-hidden="true" className="h-5 w-5" fill="none">
                  <path d={item.icon} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item.short}
              </Link>
            )
          },
        )}
      </nav>
    </>
  )
}
