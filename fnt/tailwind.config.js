/** @type {import('tailwindcss').Config} */

/*
 * Tokens for every surface. See DESIGN.md — that file is the source of truth and
 * carries the measured contrast table these values were checked against. A raw
 * hex in a component is a bug.
 *
 * Colours resolve through CSS variables declared in src/index.css, as
 * space-separated RGB triples, so Tailwind's opacity modifiers (`bg-ink/90`)
 * keep working and the dark theme is a second set of values rather than a
 * second set of classes.
 *
 * `slate` is left alone: AppShell is shared with the admin surface and still
 * uses the default scale.
 */
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Grounds, back to front.
        paper: token('paper'),
        sunken: token('sunken'),
        surface: token('surface'),
        // Text and rules.
        ink: token('ink'),
        mute: token('mute'),
        hairline: token('hairline'),
        'focus-tint': token('focus-tint'),
        // The one interactive accent. Never a state colour.
        accent: token('accent'),
        // State colours, and the tint each may sit on.
        attest: token('attest'),
        query: token('query'),
        seal: token('seal'),
        'attest-tint': token('attest-tint'),
        'query-tint': token('query-tint'),
        'seal-tint': token('seal-tint'),
      },
      fontFamily: {
        // Voice. Titles, verdicts, the numbers on a metric tile.
        display: ['"Bricolage Grotesque"', '"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        // Language.
        sans: ['"IBM Plex Sans"', 'system-ui', '"Segoe UI"', 'Roboto', 'sans-serif'],
        // Anything measured, cited or timestamped. Tabular by construction.
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      /*
       * Seven steps, in px rather than rem. The base is 17px for a phone read at
       * arm's length in glare; expressing type in rem off a 17px root would drag
       * Tailwind's 4px spacing scale to 4.25px with it.
       */
      fontSize: {
        hero: ['clamp(38px, 9vw, 64px)', { lineHeight: '1.02', letterSpacing: '-0.035em', fontWeight: '650' }],
        display: ['clamp(34px, 8vw, 44px)', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '650' }],
        title: ['28px', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '600' }],
        section: ['21px', { lineHeight: '1.3', letterSpacing: '-0.01em', fontWeight: '600' }],
        body: ['17px', { lineHeight: '1.55', fontWeight: '400' }],
        secondary: ['15px', { lineHeight: '1.5', fontWeight: '400' }],
        label: ['13px', { lineHeight: '1.35', fontWeight: '500' }],
      },
      borderRadius: {
        ctl: '12px',
        card: '20px',
        sheet: '28px',
      },
      boxShadow: {
        // Three levels, each a tight contact shadow plus a wide ambient one.
        e1: '0 1px 1px rgb(var(--c-shadow) / 0.05), 0 2px 6px -1px rgb(var(--c-shadow) / 0.07)',
        e2: '0 1px 2px rgb(var(--c-shadow) / 0.06), 0 10px 24px -6px rgb(var(--c-shadow) / 0.14)',
        e3: '0 2px 4px rgb(var(--c-shadow) / 0.08), 0 28px 56px -12px rgb(var(--c-shadow) / 0.28)',
        // The top edge light on a raised surface. Reads as thickness.
        rim: 'inset 0 1px 0 rgb(var(--c-rim) / var(--rim-alpha))',
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.22, 1, 0.36, 1)',
        'in-out': 'cubic-bezier(0.65, 0, 0.35, 1)',
      },
      transitionDuration: {
        fast: '120ms',
        base: '220ms',
        slow: '420ms',
      },
      backgroundImage: {
        // The INSUFFICIENT EVIDENCE ground. A channel in its own right — it has
        // to survive desaturation, so it is geometry and not a tint.
        hatch: 'repeating-linear-gradient(45deg, rgb(var(--c-hatch)) 0 1px, transparent 1px 6px)',
      },
      borderWidth: {
        // The FAIL left edge, and the focused-row ink bar.
        5: '5px',
      },
      minHeight: {
        // Minimum touch target. Officers use this standing up, one-handed.
        target: '48px',
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        shimmer: 'shimmer 1.6s cubic-bezier(0.65, 0, 0.35, 1) infinite',
      },
    },
  },
  plugins: [],
}
