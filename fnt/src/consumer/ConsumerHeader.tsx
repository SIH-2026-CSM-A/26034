import { Link } from 'react-router-dom'
import { Logo } from '../ui/Logo'
import { ThemeToggle } from '../ui/ThemeToggle'

export function ConsumerHeader({ title }: { title?: string }) {
  return (
    <header className="glass sticky top-0 z-30 border-b border-hairline/60">
      <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-3 px-4 py-1.5">
        <Link to="/consumer" className="flex min-h-target min-w-0 items-center gap-2.5">
          <Logo />
          <span className="font-display text-body font-semibold tracking-tight">ClauseCam</span>
          {title && <span className="truncate text-label text-mute">{title}</span>}
        </Link>
        <div className="flex shrink-0 items-center gap-1">
          <ThemeToggle />
          <Link to="/login" className="btn btn-ghost px-3 text-label text-mute">
            Officer sign-in
          </Link>
        </div>
      </div>
    </header>
  )
}
