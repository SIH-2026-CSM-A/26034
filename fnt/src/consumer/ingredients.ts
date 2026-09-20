import type { components } from '../services/generated/schema'

type PanelSpan = components['schemas']['PanelSpan']

// A heading that ends the ingredient list. Everything on a label after "Ingredients"
// up to the next such heading is shown verbatim; nothing is normalised or reordered.
const NEXT_HEADING =
  /\b(nutrition|nutritional|allergen|contains|storage|store\b|mfd|mfg|manufactured|packed|marketed|net\s*(wt|qty|quantity)|mrp|best\s*before|use\s*by|expiry|batch|lot\s*no|customer\s*care|fssai|lic)/i

// A heading that opens a block of its own and therefore always ends the declaration:
// the nutrition table, the allergen line, storage, the maker's block. The other
// headings in NEXT_HEADING are inline labels with a short value ("BATCH NO.:", "MRP",
// "NET WT") that a label prints beside the declaration, and vision may read between its
// rows.
const SECTION_HEADING =
  /\b(nutrition|nutritional|allergen|contains|storage|store\b|manufactured|packed|marketed|customer\s*care)/i

// A span that reads as part of a comma-separated ingredient list, or names an additive
// code. Vision reads a label in rows, so a nutrition table or a "BATCH NO.:" printed
// beside the declaration lands between its spans; where list text resumes within a
// few spans of a heading, the heading interrupted the declaration and did not end it.
const LIST_TEXT = /,|[([]\s*\d{3,4}/
const LOOKAHEAD = 3

/**
 * Whether the declaration resumes after the heading at `rest[i]`: list text within the
 * next few spans, with no second heading before it. Two headings in a row are the label
 * moving on; a single one is a table row or a "BATCH NO.:" printed alongside.
 */
function resumesAfter(rest: readonly PanelSpan[], i: number): boolean {
  for (const span of rest.slice(i + 1, i + 1 + LOOKAHEAD)) {
    if (NEXT_HEADING.test(span.text)) return false
    if (LIST_TEXT.test(span.text)) return true
  }
  return false
}

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
  const rest = spans.slice(start + 1)
  for (let i = 0; i < rest.length; i++) {
    const text = rest[i]!.text
    if (NEXT_HEADING.test(text)) {
      // A declaration that has reached its full stop is over; "(223)." then "CONTAINS
      // WHEAT." is the end of the list, not a table row in the middle of it.
      const closed = /\.\s*$/.test(parts[parts.length - 1] ?? '')
      if (closed || SECTION_HEADING.test(text) || !resumesAfter(rest, i)) break
      continue
    }
    parts.push(text)
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
  // Three or four digits: INS numbers run to 1xxx (the enzymes), written "1101(i)".
  // The letter suffix is attached ("472e"); "500 g" is a weight. Nothing alphanumeric
  // may follow, so a licence number's digit run and "1800 000" are not codes.
  const re = /(\b(?:INS|E)\s*-?\s*|[([]\s*)?\b(\d{3,4})(\([ivx]+\))?([a-h])?(?![a-z0-9])/gi
  for (const m of text.matchAll(re)) {
    const prefixed = /^(?:INS|E)/i.test(m[1] ?? '')
    const bracketed = /^[([]/.test(m[1] ?? '')
    const roman = m[3] ? m[3].toLowerCase() : ''
    const letter = m[4] ? m[4].toLowerCase() : ''
    // A bare number with no prefix, no suffix and no bracket around it is more often a
    // weight or a licence number than an additive; require one of the four. A bracketed
    // bare number is how a label writes "(223)" at the end of an additive list.
    if (!prefixed && !bracketed && !roman && !letter) continue
    found.add(`${m[2]}${roman}${letter}`)
  }
  return [...found]
}
