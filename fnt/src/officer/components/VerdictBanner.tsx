import { Verdict } from '../../fixtures/contracts'

/**
 * The package-level recommendation, at banner scale.
 *
 * The three verdicts are distinguished by **rule weight**, not by colour and
 * not by icon shape, so a verdict can never be mistaken for a field state:
 * field-state chips use no rules at all. A banner and a chip are different
 * kinds of object before they are different colours.
 *
 *   PASS                 solid rule
 *   REVIEW               dashed rule
 *   POTENTIAL VIOLATION  double rule, and the heaviest object on the screen
 *
 * Every banner carries "Pending officer confirmation". The system recommends
 * and a human confirms; there is no verdict for a confirmed breach, and the
 * enum has three members for that reason.
 */

interface VerdictPresentation {
  label: string
  /** Rule treatment above and below the label. The distinguishing channel. */
  rule: string
  text: string
  /** Extra weight for POTENTIAL VIOLATION, which must dominate the screen. */
  emphasis: string
}

const PRESENTATION: Record<Verdict, VerdictPresentation> = {
  [Verdict.PASS]: {
    label: 'PASS',
    rule: 'border-y-2 border-solid border-attest',
    text: 'text-attest',
    emphasis: 'py-5',
  },
  [Verdict.REVIEW]: {
    label: 'REVIEW',
    rule: 'border-y-2 border-dashed border-query',
    text: 'text-query',
    emphasis: 'py-5',
  },
  [Verdict.POTENTIAL_VIOLATION]: {
    label: 'POTENTIAL VIOLATION',
    rule: 'border-y-8 border-double border-seal',
    text: 'text-seal',
    emphasis: 'py-7',
  },
}

export function verdictLabel(verdict: Verdict): string {
  return PRESENTATION[verdict].label
}

interface VerdictBannerProps {
  verdict: Verdict
}

export function VerdictBanner({ verdict }: VerdictBannerProps) {
  const { label, rule, text, emphasis } = PRESENTATION[verdict]
  return (
    <section aria-labelledby="verdict-heading" className={`${rule} ${emphasis}`}>
      <h2 id="verdict-heading" className={`text-display ${text}`}>
        {label}
      </h2>
      <p className="mt-2 text-secondary text-mute">Pending officer confirmation</p>
    </section>
  )
}

/**
 * Queue-row scale. Keeps the rule treatment — that is the channel — and drops
 * the display size and the confirmation line, which belong to a screen that
 * shows one verdict rather than forty.
 */
export function VerdictTag({ verdict }: VerdictBannerProps) {
  const { label, rule, text } = PRESENTATION[verdict]
  return (
    <span className={`inline-block px-2 py-1 text-label ${rule} ${text}`}>{label}</span>
  )
}
