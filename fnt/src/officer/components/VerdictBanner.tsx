import { motion } from 'framer-motion'
import type { components } from '../../services/generated/schema'
import { spring } from '../../ui/motion'

type Verdict = components['schemas']['Verdict']

/**
 * The package-level recommendation, at banner scale.
 *
 * Each verdict is an icon, the word and a colour together, and the three are
 * further separated by **rule weight**, so a verdict can never be mistaken for a
 * field state: field-state chips use no full outline rule of this weight. A banner and a chip are different
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

interface IconProps {
  className?: string
}

/** PASS. A tick inside a seal — a whole, closed shape. */
function PassIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none">
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeWidth="2" />
      <path d="m7.5 12.4 3 3 6-6.6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** REVIEW. An eye: a person has to look at this one. */
function ReviewIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none">
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.8" fill="currentColor" />
    </svg>
  )
}

/** POTENTIAL VIOLATION. A warning triangle — the only angular icon of the three. */
function PotentialViolationIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none">
      <path d="M12 3.2 22 20.5H2L12 3.2Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M12 9.5v5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="12" cy="17.3" r="1.3" fill="currentColor" />
    </svg>
  )
}

interface VerdictPresentation {
  label: string
  Icon: (props: IconProps) => JSX.Element
  /** Rule treatment around the label. The channel that survives greyscale. */
  rule: string
  text: string
  /** The only ground a verdict colour may sit on besides paper and surface. */
  tint: string
  /** Extra weight for POTENTIAL VIOLATION, which must dominate the screen. */
  emphasis: string
}

const PRESENTATION: Record<Verdict, VerdictPresentation> = {
  PASS: {
    label: 'PASS',
    Icon: PassIcon,
    rule: 'border-2 border-solid border-attest',
    text: 'text-attest',
    tint: 'bg-attest-tint',
    emphasis: 'py-5',
  },
  REVIEW: {
    label: 'REVIEW',
    Icon: ReviewIcon,
    rule: 'border-2 border-dashed border-query',
    text: 'text-query',
    tint: 'bg-query-tint',
    emphasis: 'py-5',
  },
  POTENTIAL_VIOLATION: {
    label: 'POTENTIAL VIOLATION',
    Icon: PotentialViolationIcon,
    rule: 'border-[6px] border-double border-seal',
    text: 'text-seal',
    tint: 'bg-seal-tint',
    emphasis: 'py-7',
  },
}

export function verdictLabel(verdict: Verdict): string {
  return PRESENTATION[verdict].label
}

interface VerdictBannerProps {
  verdict: Verdict
}

/**
 * Icon, word and colour together, plus the rule weight — four channels. The word
 * is in the DOM on first render; the entrance is a transform on a node that
 * already holds it, so nothing a screen reader or an officer needs is ever
 * waiting on an animation.
 */
export function VerdictBanner({ verdict }: VerdictBannerProps) {
  const { label, Icon, rule, text, tint, emphasis } = PRESENTATION[verdict]
  return (
    <motion.section
      aria-labelledby="verdict-heading"
      initial={{ opacity: 0.6, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={spring.glide}
      className={`rounded-card px-5 shadow-e2 sm:px-7 ${rule} ${tint} ${emphasis}`}
    >
      <div className={`flex items-center gap-4 ${text}`}>
        <Icon className="h-11 w-11 shrink-0 sm:h-14 sm:w-14" />
        <h2 id="verdict-heading" className="min-w-0 text-display [overflow-wrap:anywhere]">
          {label}
        </h2>
      </div>
      <p className="mt-2 text-secondary text-mute">Pending officer confirmation</p>
    </motion.section>
  )
}

/**
 * Queue-row scale. Keeps the icon and the rule treatment — those are the
 * channels — and drops the display size and the confirmation line, which belong
 * to a screen that shows one verdict rather than forty.
 */
export function VerdictTag({ verdict }: VerdictBannerProps) {
  const { label, Icon, rule, text, tint } = PRESENTATION[verdict]
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-label font-semibold ${rule} ${text} ${tint}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </span>
  )
}
