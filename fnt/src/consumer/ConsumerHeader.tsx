import { Link } from 'react-router-dom'

export function ConsumerHeader({ title }: { title?: string }) {
  return (
    <header className="border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-[960px] flex-wrap items-center justify-between gap-y-2 px-4 py-3">
        <div className="flex items-baseline gap-x-4">
          <Link to="/consumer" className="text-label font-bold tracking-wider text-ink">
            PCCS
          </Link>
          <span className="font-mono text-label text-mute">Consumer{title ? ` / ${title}` : ''}</span>
        </div>
        <Link to="/login" className="flex min-h-target items-center text-label text-mute hover:text-ink">
          Officer sign-in →
        </Link>
      </div>
    </header>
  )
}
