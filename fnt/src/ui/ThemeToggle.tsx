import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { spring } from './motion'

type Theme = 'light' | 'dark'

function currentTheme(): Theme {
  const set = document.documentElement.dataset.theme
  if (set === 'light' || set === 'dark') return set
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Light / dark switch. The knob is a spring, so a tap feels like a throw rather
 * than a fade. The choice is kept in localStorage and applied before first paint
 * by the inline script in index.html.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('pccs-theme', theme)
    } catch {
      // Private mode. The switch still works for this page view.
    }
  }, [theme])

  const dark = theme === 'dark'
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label="Dark appearance"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      className="flex min-h-target items-center px-1"
    >
      <span
        className={`flex h-7 w-12 items-center rounded-full border border-hairline bg-sunken p-0.5 shadow-[inset_0_1px_2px_rgb(var(--c-shadow)/0.12)] ${dark ? 'justify-end' : 'justify-start'}`}
      >
        <motion.span
          layout
          transition={spring.snap}
          whileTap={{ scaleX: 1.18 }}
          className="flex h-[22px] w-[22px] items-center justify-center rounded-full bg-surface text-ink shadow-e2"
        >
          <svg viewBox="0 0 16 16" aria-hidden="true" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            {dark ? (
              <path d="M13 9.6A5.6 5.6 0 0 1 6.4 3a5.6 5.6 0 1 0 6.6 6.6Z" fill="currentColor" stroke="none" />
            ) : (
              <>
                <circle cx="8" cy="8" r="2.8" fill="currentColor" stroke="none" />
                <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1" />
              </>
            )}
          </svg>
        </motion.span>
      </span>
    </button>
  )
}
