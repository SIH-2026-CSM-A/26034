// WCAG 2.1 contrast for every text-on-ground pair the design system allows, read
// straight from src/index.css so the table in DESIGN.md cannot drift from the tokens.
// Exits 1 if any text pair is under 4.5:1.  Run: node scripts/contrast.mjs
import { readFileSync } from 'node:fs'

const css = readFileSync(new URL('../src/index.css', import.meta.url), 'utf8')
const block = (re) => Object.fromEntries(
  [...css.match(re)[1].matchAll(/--c-([\w-]+):\s*(\d+) (\d+) (\d+)/g)].map(([, k, r, g, b]) => [k, [+r, +g, +b]]),
)
const themes = {
  light: block(/:root \{([^}]+)\}/),
  dark: block(/:root\[data-theme='dark'\] \{([^}]+)\}/),
}
const lum = (rgb) => {
  const [r, g, b] = rgb.map((v) => ((v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const ratio = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}
const PAIRS = [
  ...['ink', 'mute', 'accent', 'attest', 'query', 'seal'].flatMap((fg) =>
    ['paper', 'surface', 'sunken', 'focus-tint'].map((bg) => [fg, bg])),
  ['attest', 'attest-tint'], ['query', 'query-tint'], ['seal', 'seal-tint'],
  ['paper', 'ink'], ['paper', 'attest'],
]
let failed = 0
for (const [name, t] of Object.entries(themes)) {
  console.log(`\n${name}`)
  for (const [fg, bg] of PAIRS) {
    const r = ratio(t[fg], t[bg])
    if (r < 4.5) failed += 1
    console.log(`  ${r < 4.5 ? 'FAIL' : ' ok '}  ${r.toFixed(2).padStart(5)}  ${fg} on ${bg}`)
  }
}
process.exit(failed ? 1 : 0)
