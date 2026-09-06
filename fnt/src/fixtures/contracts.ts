/**
 * A hand-written TypeScript mirror of the backend `app.contracts` package.
 *
 * This file is a stand-in with a known expiry. The real client is generated
 * from the backend OpenAPI schema into `src/services/generated/`, and when
 * that lands these types are deleted and the imports repointed — they are not
 * a parallel definition to be maintained. Field names are snake_case because
 * that is what the API emits; nothing here renames a contract field.
 *
 * Two enums and four record types, matching bck/app/contracts/enums.py and
 * bck/app/contracts/records.py. Widening either enum on this side would let
 * the frontend render a state the backend cannot produce, so both are `const`
 * objects with a derived union rather than open string types.
 */

/**
 * Five states, deliberately. Four would force "we could not read it" and
 * "it is not there" into the same bucket, which is a wrongful-flag liability
 * rather than a style choice.
 */
export const FieldState = {
  /** Present, legible, and satisfies the rule as evaluated. */
  PASS: 'PASS',
  /** Read successfully and falls short. A positive finding about the package. */
  FAIL: 'FAIL',
  /** Evidence is legible, but applying the rule to it needs a person. */
  REVIEW_REQUIRED: 'REVIEW_REQUIRED',
  /** A statutory carve-out removes the obligation. Not a lesser PASS. */
  NOT_APPLICABLE: 'NOT_APPLICABLE',
  /** The evidence needed could not be obtained. A statement about the
   *  observation, never about the package. Never interchangeable with FAIL. */
  INSUFFICIENT_EVIDENCE: 'INSUFFICIENT_EVIDENCE',
} as const
export type FieldState = (typeof FieldState)[keyof typeof FieldState]

/**
 * Three members. The system recommends and a human confirms, so there is no
 * member for a confirmed breach.
 */
export const Verdict = {
  PASS: 'PASS',
  REVIEW: 'REVIEW',
  POTENTIAL_VIOLATION: 'POTENTIAL_VIOLATION',
} as const
export type Verdict = (typeof Verdict)[keyof typeof Verdict]

/** Rule 6 declaration obligations, one member per clause. */
export const DeclarationField = {
  NAME_AND_ADDRESS: 'NAME_AND_ADDRESS',
  COUNTRY_OF_ORIGIN: 'COUNTRY_OF_ORIGIN',
  COMMON_OR_GENERIC_NAME: 'COMMON_OR_GENERIC_NAME',
  NET_QUANTITY: 'NET_QUANTITY',
  MANUFACTURE_DATE: 'MANUFACTURE_DATE',
  BEST_BEFORE_DATE: 'BEST_BEFORE_DATE',
  RETAIL_SALE_PRICE: 'RETAIL_SALE_PRICE',
  DIMENSIONS: 'DIMENSIONS',
  OTHER_PRESCRIBED_MATTER: 'OTHER_PRESCRIBED_MATTER',
  CONSUMER_CARE: 'CONSUMER_CARE',
  UNIT_SALE_PRICE: 'UNIT_SALE_PRICE',
} as const
export type DeclarationField = (typeof DeclarationField)[keyof typeof DeclarationField]

/** What produced a piece of evidence. */
export const EvidenceProvider = {
  PADDLEOCR: 'PADDLEOCR',
  TESSERACT: 'TESSERACT',
  CLOUD_OCR: 'CLOUD_OCR',
  ARTWORK: 'ARTWORK',
  CATALOGUE: 'CATALOGUE',
  MANUAL: 'MANUAL',
} as const
export type EvidenceProvider = (typeof EvidenceProvider)[keyof typeof EvidenceProvider]

export type RuleStatus = 'VERIFIED' | 'UNVERIFIED'
export type RuleSeverity = 'MANDATORY' | 'CONDITIONAL' | 'ADVISORY'

/**
 * The rule as it stood at the moment of evaluation, copied by value.
 *
 * Not a reference to a rule row. Joining a stored verdict back to a live rules
 * table would re-adjudicate history — an amendment landing on Tuesday would
 * silently change what Monday's scan is recorded as having found. The UI reads
 * the snapshot for the same reason: what it displays is what was decided, not
 * what the rule says today.
 */
export interface RuleParameterSnapshot {
  rule_id: string
  clause_ref: string
  gazette_ref: string
  source_text: string
  status: RuleStatus
  severity: RuleSeverity
  rule_set_version: string
}

/** The outcome of evaluating one declaration against one rule, with evidence. */
export interface FieldFinding {
  field: DeclarationField
  state: FieldState
  rule_snapshot: RuleParameterSnapshot
  /** What was read off the package, canonicalised. `null` where nothing was read. */
  observed_value: string | null
  /** What the rule required, where it states a specific value or format. */
  expected_value: string | null
  /**
   * Why this state was reached, in terms a reviewing officer can act on. For
   * INSUFFICIENT_EVIDENCE this is what could not be read and why, never a
   * guess at what the package says.
   */
  reason: string
  evidence_span_ids: readonly string[]
}

/** A single polygon vertex in image pixel coordinates, `[x, y]`. */
export type Point = readonly [number, number]

/**
 * One run of text located on an image, as reported by a text provider.
 *
 * Raw observation — no interpretation of what the text means has happened yet.
 * Confidence and polygon live here rather than on the finding, which is why the
 * ledger resolves a row's confidence through `evidence_span_ids` instead of
 * reading it off the finding directly. A finding made because nothing could be
 * read cites no spans, and so has neither.
 */
export interface ExtractedSpan {
  span_id: string
  text: string
  /**
   * The span's outline in image pixel coordinates. Not a bounding box: labels
   * on cylindrical packages are not axis-aligned, and the crop an officer is
   * shown has to match what was actually read.
   */
  polygon: readonly Point[]
  /** The provider's own confidence. Provider-relative, not comparable across
   *  providers without calibration. */
  confidence: number
  source_provider: EvidenceProvider
  region_id: string
}

/** The complete, self-contained record of one evaluation. */
export interface VerdictRecord {
  subject_ref: string
  verdict: Verdict
  rule_set_version: string
  evaluated_at: string
  findings: readonly FieldFinding[]
  field_providers: Partial<Record<DeclarationField, EvidenceProvider>>
}
