/** @type {import('tailwindcss').Config} */

/*
 * Tokens for the officer surface. See DESIGN.md — that file is the source of
 * truth and carries the measured contrast table these values were checked
 * against. A raw hex in a component is a bug.
 *
 * Colour names are semantic and deliberately avoid Tailwind's own scale names.
 * `slate` is left alone: AppShell is shared with the admin surface and still
 * uses the default scale, and overriding it here would restyle someone else's
 * screens from this file.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#DCDFDB',
        ink: '#101A24',
        attest: '#14603C',
        query: '#845605',
        seal: '#A32A1E',
        mute: '#4A5560',
        hairline: '#A8AFAC',
        'focus-tint': '#C9CEC9',
      },
      fontFamily: {
        // Language.
        sans: ['"IBM Plex Sans"', 'system-ui', '"Segoe UI"', 'Roboto', 'sans-serif'],
        // Anything measured, cited or timestamped. Tabular by construction.
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      /*
       * Six steps, in px rather than rem. The base is 17px for a phone read at
       * arm's length in glare; expressing type in rem off a 17px root would drag
       * Tailwind's 4px spacing scale to 4.25px with it.
       */
      fontSize: {
        display: ['44px', { lineHeight: '1.05', letterSpacing: '-0.02em', fontWeight: '600' }],
        title: ['27px', { lineHeight: '1.18', letterSpacing: '-0.01em', fontWeight: '600' }],
        section: ['21px', { lineHeight: '1.3', fontWeight: '500' }],
        body: ['17px', { lineHeight: '1.55', fontWeight: '400' }],
        secondary: ['15px', { lineHeight: '1.5', fontWeight: '400' }],
        label: ['13px', { lineHeight: '1.35', fontWeight: '500' }],
      },
      backgroundImage: {
        // The INSUFFICIENT EVIDENCE ground. A channel in its own right — it has
        // to survive desaturation, so it is geometry and not a tint.
        hatch: 'repeating-linear-gradient(45deg, #A8AFAC 0 1px, transparent 1px 6px)',
      },
      borderWidth: {
        // The FAIL left edge, and the focused-row ink bar.
        5: '5px',
      },
      minHeight: {
        // Minimum touch target. Officers use this standing up, one-handed.
        target: '48px',
      },
    },
  },
  plugins: [],
}
