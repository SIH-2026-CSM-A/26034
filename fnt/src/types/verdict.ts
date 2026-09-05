/**
 * Overall verdict types defined by Legal Metrology (Packaged Commodities) Rules, 2011 compliance system.
 *
 * STANDING CONSTRAINT:
 * Verdicts are strictly PASS / REVIEW / POTENTIAL VIOLATION.
 * NEVER "violation confirmed", NEVER "non-compliant".
 */
export type OverallVerdict = 'PASS' | 'REVIEW' | 'POTENTIAL_VIOLATION';

/**
 * Per-field findings state.
 * INSUFFICIENT_EVIDENCE is distinct from POTENTIAL_VIOLATION ("we could not read it" vs "it is not there").
 */
export type FieldFindingState =
  | 'PASS'
  | 'REVIEW'
  | 'POTENTIAL_VIOLATION'
  | 'INSUFFICIENT_EVIDENCE'
  | 'EXEMPT';

export interface VerdictMeta {
  readonly code: OverallVerdict;
  readonly label: string;
  readonly symbol: string;
  readonly description: string;
  readonly ariaLabel: string;
}

export const VERDICT_CONFIG: Record<OverallVerdict, VerdictMeta> = {
  PASS: {
    code: 'PASS',
    label: 'PASS',
    symbol: '✓',
    description: 'All mandatory declarations verified compliant with LMPC Rules 2011.',
    ariaLabel: 'Verdict: PASS. Compliant with LMPC rules.',
  },
  REVIEW: {
    code: 'REVIEW',
    label: 'REVIEW',
    symbol: '⚠',
    description: 'Field requires human officer confirmation or uncalibrated estimate inspection.',
    ariaLabel: 'Verdict: REVIEW. Requires human officer verification.',
  },
  POTENTIAL_VIOLATION: {
    code: 'POTENTIAL_VIOLATION',
    label: 'POTENTIAL VIOLATION',
    symbol: '✕',
    description: 'Potential discrepancy detected against specified LMPC statutory clause.',
    ariaLabel: 'Verdict: POTENTIAL VIOLATION. Discrepancy flagged for human determination.',
  },
} as const;
