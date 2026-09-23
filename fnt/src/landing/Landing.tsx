import { type Transition, motion, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '../ui/Logo'

/**
 * The public root. A 2.9 s opening — a pack, its label panel, clause lines resolving onto
 * it, the scan frame closing — then the wordmark and the ways in.
 *
 * It never gates anything: the entry links are in the DOM from the first frame, only `/`
 * plays it (a deep link never mounts this), any click or key skips it, and it plays once
 * per tab session, so a reload mid-opening lands on the final frame. Reduced motion
 * renders the final frame directly.
 */
const PLAYED_KEY = 'clausecam.opening-played'
const LENGTH_MS = 2900

function playedThisSession(): boolean {
  try {
    return sessionStorage.getItem(PLAYED_KEY) === '1'
  } catch {
    return false
  }
}

const EASE = [0.22, 1, 0.36, 1] as const

const CLAUSES = [
  { width: 52, state: 'attest' },
  { width: 64, state: 'attest' },
  { width: 44, state: 'query' },
  { width: 58, state: 'attest' },
  { width: 38, state: 'attest' },
] as const

const ENTRIES = [
  { to: '/login', title: 'Officer', body: 'Legal Metrology inspectors. Scan, review, escalate.' },
  { to: '/vendor/login', title: 'Vendor', body: 'Self-check your own stock before an inspector does.' },
  { to: '/consumer', title: 'Consumer', body: 'Check a package label. No sign-in.' },
  {
    to: '/officer/vendors',
    title: 'Create account',
    body: 'An officer registers a vendor premises and issues its login.',
  },
] as const

export function Landing() {
  const reduceMotion = useReducedMotion()
  const [instant, setInstant] = useState(() => Boolean(reduceMotion) || playedThisSession())

  useEffect(() => {
    try {
      sessionStorage.setItem(PLAYED_KEY, '1')
    } catch {
      // Storage refused (private mode): the opening simply plays again next time.
    }
    if (instant) return
    const skip = () => setInstant(true)
    const timer = window.setTimeout(skip, LENGTH_MS)
    window.addEventListener('keydown', skip)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('keydown', skip)
    }
  }, [instant])

  // `initial={false}` renders the target state with no animation, so skipping remounts
  // the stage (the key) straight onto the final frame.
  const from = <T,>(start: T) => (instant ? false : start)
  const at = (delay: number, duration = 0.45): Transition => ({ delay, duration, ease: EASE })

  return (
    <div className="aurora flex min-h-screen flex-col">
      <main
        key={instant ? 'final' : 'opening'}
        className="mx-auto flex w-full max-w-[880px] flex-1 flex-col items-center justify-center px-4 py-10"
        onClick={instant ? undefined : () => setInstant(true)}
      >
        <svg viewBox="0 0 200 232" aria-hidden="true" className="h-auto w-[168px] sm:w-[200px]">
          <motion.g
            initial={from({ opacity: 0, y: 18, scale: 0.94 })}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={at(0, 0.5)}
            className="origin-center [transform-box:fill-box]"
          >
            <path d="M36 42 56 24h124l-20 18Z" className="fill-sunken stroke-hairline" strokeWidth="1.5" />
            <path d="M160 42 180 24v166l-20 18Z" className="fill-sunken stroke-hairline" strokeWidth="1.5" />
            <rect x="36" y="42" width="124" height="166" rx="8" className="fill-surface stroke-hairline" strokeWidth="1.5" />
          </motion.g>

          <motion.rect
            x="52"
            y="68"
            width="92"
            height="116"
            rx="4"
            className="origin-top fill-paper stroke-ink/25 [transform-box:fill-box]"
            strokeWidth="1.5"
            initial={from({ scaleY: 0, opacity: 0 })}
            animate={{ scaleY: 1, opacity: 1 }}
            transition={at(0.35, 0.45)}
          />

          {CLAUSES.map((clause, i) => {
            const y = 84 + i * 19
            return (
              <g key={y}>
                <motion.rect
                  x="62"
                  y={y - 2.5}
                  width={clause.width}
                  height="5"
                  rx="2.5"
                  className="fill-ink/70"
                  initial={from({ x: 70, opacity: 0 })}
                  animate={{ x: 0, opacity: 1 }}
                  transition={at(0.7 + i * 0.13, 0.4)}
                />
                <motion.g
                  initial={from({ scale: 0, opacity: 0 })}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={at(1.0 + i * 0.13, 0.3)}
                  className="origin-center [transform-box:fill-box]"
                >
                  <circle cx="132" cy={y} r="5.5" className={clause.state === 'attest' ? 'fill-attest' : 'fill-query'} />
                  {clause.state === 'attest' ? (
                    <path d={`m129.5 ${y + 0.2} 1.8 1.8 3.3-3.6`} className="stroke-paper" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  ) : (
                    <path d={`M132 ${y - 2.6}v3M132 ${y + 2.3}v.1`} className="stroke-paper" strokeWidth="1.6" strokeLinecap="round" />
                  )}
                </motion.g>
              </g>
            )
          })}

          <motion.path
            d="M44 72v-8a4 4 0 0 1 4-4h8M140 60h8a4 4 0 0 1 4 4v8M152 180v8a4 4 0 0 1-4 4h-8M56 192h-8a4 4 0 0 1-4-4v-8"
            className="origin-center stroke-accent [transform-box:fill-box]"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
            initial={from({ scale: 1.22, opacity: 0 })}
            animate={{ scale: 1, opacity: 1 }}
            transition={at(1.7, 0.35)}
          />
        </svg>

        <motion.div
          className="mt-6 flex items-center gap-3"
          initial={from({ opacity: 0, y: 12 })}
          animate={{ opacity: 1, y: 0 }}
          transition={at(2.0, 0.4)}
        >
          <Logo className="h-10 w-10 sm:h-12 sm:w-12" />
          <h1 className="font-display text-hero">ClauseCam</h1>
        </motion.div>
        <motion.p
          className="mt-2 text-center text-secondary text-mute"
          initial={from({ opacity: 0 })}
          animate={{ opacity: 1 }}
          transition={at(2.1, 0.4)}
        >
          Packaged Commodity Compliance System · Legal Metrology (Packaged Commodities) Rules, 2011
        </motion.p>

        <nav aria-label="Ways in" className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
          {ENTRIES.map((entry, i) => (
            <motion.div
              key={entry.to}
              initial={from({ opacity: 0, y: 10 })}
              animate={{ opacity: 1, y: 0 }}
              transition={at(2.25 + i * 0.07, 0.4)}
            >
              <Link to={entry.to} className="card block h-full p-5 transition-shadow hover:shadow-e2">
                <span className="text-section">{entry.title}</span>
                <span className="mt-1 block text-secondary text-mute">{entry.body}</span>
              </Link>
            </motion.div>
          ))}
        </nav>
      </main>

      {!instant && (
        <button
          type="button"
          onClick={() => setInstant(true)}
          className="btn btn-quiet fixed right-4 top-4 text-secondary"
        >
          Skip
        </button>
      )}
    </div>
  )
}
