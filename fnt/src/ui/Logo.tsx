/** The Maapdand mark: a scan frame closing on a tick. Same drawing as public/favicon.svg. */
export function Logo({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className} fill="none">
      <rect width="32" height="32" rx="8" className="fill-ink" />
      <path
        d="M9 12.5V10a1 1 0 0 1 1-1h2.5M19.5 9H22a1 1 0 0 1 1 1v2.5M23 19.5V22a1 1 0 0 1-1 1h-2.5M12.5 23H10a1 1 0 0 1-1-1v-2.5"
        className="stroke-paper"
        strokeOpacity="0.55"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="m11.5 16.3 3.2 3.2 6-6.8"
        className="stroke-attest-tint"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
