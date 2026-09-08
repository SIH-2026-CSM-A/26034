import type { components } from '../services/generated/schema'

type FieldFinding = components['schemas']['FieldFinding']
type FieldState = components['schemas']['FieldState']
type Verdict = components['schemas']['Verdict']

/** What each declaration is, in the words a shopper would use. */
export const FIELD_LABEL: Record<string, string> = {
  NAME_AND_ADDRESS: 'Who made or packed it, and where',
  COUNTRY_OF_ORIGIN: 'Country of origin',
  COMMON_OR_GENERIC_NAME: 'What the product is (its common name)',
  NET_QUANTITY: 'How much is in the pack (net quantity)',
  MANUFACTURE_DATE: 'When it was made or packed',
  BEST_BEFORE_DATE: 'Best before or use-by date',
  RETAIL_SALE_PRICE: 'Maximum retail price (MRP)',
  DIMENSIONS: 'Size of the commodity, where the rules ask for it',
  OTHER_PRESCRIBED_MATTER: 'Other particulars the rules prescribe',
  CONSUMER_CARE: 'Consumer care contact',
  UNIT_SALE_PRICE: 'Unit sale price',
}

/**
 * What a field state means to a shopper. INSUFFICIENT_EVIDENCE is worded as a fact
 * about the photograph, never about the package, and FAIL is a recommendation for an
 * officer to confirm, never a confirmed breach.
 */
export const STATE_SENTENCE: Record<FieldState, string> = {
  PASS: 'Found on the label.',
  FAIL: 'Appears to be missing or not as the rules require. An officer would confirm this.',
  REVIEW_REQUIRED: 'Readable on the label, but applying the rule needs a person to look.',
  NOT_APPLICABLE: 'The rules do not require this for this kind of package.',
  INSUFFICIENT_EVIDENCE:
    'Could not be read from this photograph. That is not a finding that it is absent.',
}

export const VERDICT_SENTENCE: Record<Verdict, string> = {
  PASS: 'Every declaration that could be checked from this photograph was found as the rules require.',
  REVIEW:
    'Some declarations could not be verified from this photograph. Nothing here says the package is non-compliant.',
  POTENTIAL_VIOLATION:
    'At least one declaration appears to be missing or not as the rules require. This is a recommendation for a Legal Metrology officer to check, not a confirmed breach.',
}

const SEVERITY: Record<FieldState, number> = {
  FAIL: 4,
  REVIEW_REQUIRED: 3,
  INSUFFICIENT_EVIDENCE: 2,
  PASS: 1,
  NOT_APPLICABLE: 0,
}

export interface FieldSummary {
  field: string
  label: string
  /** The state a shopper should read first: a PASS with what was read, else the worst. */
  state: FieldState
  observed: string | null
  /** Clause references behind the headline state. */
  clauses: string[]
  /** Rules that could not be assessed from this photograph, beyond the headline. */
  unassessedClauses: string[]
}

/**
 * One line per declaration. A declaration is evaluated under several rules; the
 * shopper reads the rule that found it, and how many others could not be assessed.
 */
export function summariseByField(findings: readonly FieldFinding[]): FieldSummary[] {
  const byField = new Map<string, FieldFinding[]>()
  for (const f of findings) {
    const list = byField.get(f.field) ?? []
    list.push(f)
    byField.set(f.field, list)
  }
  const out: FieldSummary[] = []
  for (const [field, list] of byField) {
    const passes = list.filter((f) => f.state === 'PASS')
    const headline =
      passes[0] ?? [...list].sort((a, b) => SEVERITY[b.state] - SEVERITY[a.state])[0]
    if (!headline) continue
    const headlineState = headline.state
    const same = list.filter((f) => f.state === headlineState)
    const unassessed = list.filter(
      (f) => f.state === 'INSUFFICIENT_EVIDENCE' && headlineState !== 'INSUFFICIENT_EVIDENCE',
    )
    out.push({
      field,
      label: FIELD_LABEL[field] ?? field.replace(/_/g, ' ').toLowerCase(),
      state: headlineState,
      observed: headline.observed_value ?? null,
      clauses: [...new Set(same.map((f) => f.rule_snapshot.clause_ref))],
      unassessedClauses: [...new Set(unassessed.map((f) => f.rule_snapshot.clause_ref))],
    })
  }
  return out.sort((a, b) => SEVERITY[b.state] - SEVERITY[a.state])
}
