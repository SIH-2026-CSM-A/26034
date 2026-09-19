import { Link, useNavigate } from 'react-router-dom'
import { VENDOR_HOME_PATH, VENDOR_LOGIN_PATH, clearVendorToken } from '../services/vendorAuth'
import { Logo } from '../ui/Logo'
import { ThemeToggle } from '../ui/ThemeToggle'

/**
 * Vendor chrome. No officer navigation anywhere on it: the queue, the dashboard, the
 * complaints and the review controls are officer acts, and a vendor's token is refused on
 * every one of them server-side. The UI does not offer what the server would refuse.
 */
export function VendorHeader({ title, signedIn = true }: { title?: string; signedIn?: boolean }) {
  const navigate = useNavigate()
  return (
    <header className="glass sticky top-0 z-30 border-b border-hairline/60">
      <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-3 px-4 py-1.5">
        <Link to={VENDOR_HOME_PATH} className="flex min-h-target min-w-0 items-center gap-2.5">
          <Logo />
          <span className="font-display text-body font-semibold tracking-tight">PCCS</span>
          <span className="truncate text-label text-mute">Vendor self-check{title ? ` · ${title}` : ''}</span>
        </Link>
        <div className="flex shrink-0 items-center gap-1">
          <ThemeToggle />
          {signedIn && (
            <button
              type="button"
              onClick={() => {
                clearVendorToken()
                navigate(VENDOR_LOGIN_PATH, { replace: true })
              }}
              className="btn btn-ghost px-3 text-label text-mute"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
