import type { components } from '../services/generated/schema'

type PanelSpan = components['schemas']['PanelSpan']

// A heading that ends the ingredient list. Everything on a label after "Ingredients"
// up to the next such heading is shown verbatim; nothing is normalised or reordered.
const NEXT_HEADING =
  /\b(nutrition|nutritional|allergen|contains|storage|store\b|mfd|mfg|manufactured|packed|marketed|net\s*(wt|qty|quantity)|mrp|best\s*before|use\s*by|expiry|batch|lot\s*no|customer\s*care|fssai|lic)/i

/**
 * The ingredient declaration exactly as vision read it, or null if the label carries
 * no line that names one. Joined with " | " between spans, which is how the officer
 * surface shows multi-span text, so a reader can see where one line ended.
 */
export function ingredientText(spans: readonly PanelSpan[]): string | null {
  const start = spans.findIndex((s) => /ingredients?\b/i.test(s.text))
  if (start < 0) return null
  const first = (spans[start]?.text ?? '').replace(/^.*?ingredients?\s*:?\s*/i, '')
  const parts = first ? [first] : []
  for (const span of spans.slice(start + 1)) {
    if (NEXT_HEADING.test(span.text)) break
    parts.push(span.text)
  }
  return parts.length ? parts.join(' | ') : null
}

/**
 * Additive codes as written in an ingredient declaration: "INS 319", "E223", a bare
 * "503(ii)" or "472e" inside a bracketed additive list. Returned normalised to the
 * INS form without prefix, e.g. "503(ii)", "472e", "319".
 */
export function additiveCodes(text: string): string[] {
  const found = new Set<string>()
  const re = /\b(?:INS|E)?\s*-?\s*(\d{3})\s*(\([ivx]+\))?\s*([a-h])?\b/gi
  for (const m of text.matchAll(re)) {
    const prefixed = /\b(?:INS|E)\s*-?\s*\d{3}/i.test(m[0])
    const roman = m[2] ? m[2].toLowerCase() : ''
    const letter = m[3] ? m[3].toLowerCase() : ''
    // A bare three-digit number with neither a prefix nor a suffix is more often a
    // weight or a licence number than an additive; require one of the three.
    if (!prefixed && !roman && !letter) continue
    found.add(`${m[1]}${roman}${letter}`)
  }
  return [...found]
}
