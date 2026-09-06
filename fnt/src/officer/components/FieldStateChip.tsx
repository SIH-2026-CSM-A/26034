import { FieldState } from '../../fixtures/contracts'

/**
 * The five field states, each on four independent channels with colour last:
 * a glyph, a fill, a border treatment, and a weight. See DESIGN.md.
 *
 * Desaturate this component and all five must stay separable. That is the
 * shipping gate, and it is why the glyphs are drawn as SVG rather than set as
 * text characters — a glyph that depends on font coverage is a channel that
 * can silently disappear.
 *
 * FAIL and INSUFFICIENT EVIDENCE share no channel. Glyph, fill, border and
 * colour all differ, so there is no viewing condition in which one degrades
 * into the other. "We could not read it" and "it is not there" carry different
 * legal consequences, and the rendering is not allowed to blur them.
 */

interface GlyphProps {
  className?: string
}

/** PASS. A tick, drawn heavy enough to survive a washed-out panel. */
function TickGlyph({ className }: GlyphProps) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="none">
      <path
        d="M3 8.5 6.5 12 13 4.5"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="square"
      />
    </svg>
  )
}

/** FAIL. A cross — no part of it is a curve, so it cannot read as the ring. */
function CrossGlyph({ className }: GlyphProps) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="none">
      <path d="M4 4 12 12M12 4 4 12" stroke="currentColor" strokeWidth="2.25" strokeLinecap="square" />
    </svg>
  )
}

/** REVIEW REQUIRED. A question mark: the machine is asking, not asserting. */
function QueryGlyph({ className }: GlyphProps) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="none">
      <path
        d="M5.4 5.6a2.7 2.7 0 1 1 3.4 2.6c-.5.2-.8.6-.8 1.1v.6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="8" cy="12.4" r="1.15" fill="currentColor" />
    </svg>
  )
}

/** NOT APPLICABLE. An em dash — the rule does not reach this package. */
function DashGlyph({ className }: GlyphProps) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="none">
      <path d="M2.5 8h11" stroke="currentColor" strokeWidth="1.75" strokeLinecap="butt" />
    </svg>
  )
}

/** INSUFFICIENT EVIDENCE. A hollow ring: an outline around nothing. */
function RingGlyph({ className }: GlyphProps) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" className={className} fill="none">
      <circle cx="8" cy="8" r="4.9" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

interface StatePresentation {
  label: string
  Glyph: (props: GlyphProps) => JSX.Element
  /**
   * Chip classes. Unfilled chips ground explicitly on Field Paper rather than
   * inheriting the row background: Query Ochre measures 3.97:1 on the focused
   * row tint, which is below AA, and a focused REVIEW REQUIRED row would
   * otherwise drop out of compliance exactly when it is read hardest.
   * See DESIGN.md — lightening the tint instead was measured and rejected.
   */
  chip: string
  /**
   * Applied to the glyph-and-label group. INSUFFICIENT EVIDENCE plates its
   * label on Field Paper so the hatch does not run under the text: Slate Void
   * over a hatch line measures 3.4:1, below AA. The hatch stays a channel —
   * it frames the label instead of crossing it.
   */
  plate: string
  /** Announced to assistive technology, since the glyph is decorative. */
  description: string
}

const PRESENTATION: Record<FieldState, StatePresentation> = {
  [FieldState.PASS]: {
    label: 'PASS',
    Glyph: TickGlyph,
    chip: 'bg-attest text-paper font-medium border border-attest',
    plate: '',
    description: 'Pass. The declaration satisfies the rule as evaluated.',
  },
  [FieldState.FAIL]: {
    label: 'FAIL',
    Glyph: CrossGlyph,
    chip: 'bg-paper text-seal font-semibold border border-hairline border-l-5 border-l-seal',
    plate: '',
    description: 'Fail. The declaration was read and falls short of the rule.',
  },
  [FieldState.REVIEW_REQUIRED]: {
    label: 'REVIEW REQUIRED',
    Glyph: QueryGlyph,
    chip: 'bg-paper text-query font-medium border border-dashed border-query',
    plate: '',
    description: 'Review required. Applying the rule to this evidence needs an officer.',
  },
  [FieldState.NOT_APPLICABLE]: {
    label: 'NOT APPLICABLE',
    Glyph: DashGlyph,
    chip: 'bg-paper text-mute font-normal',
    plate: '',
    description: 'Not applicable. A statutory carve-out removes the obligation.',
  },
  [FieldState.INSUFFICIENT_EVIDENCE]: {
    label: 'INSUFFICIENT EVIDENCE',
    Glyph: RingGlyph,
    chip: 'bg-paper bg-hatch text-mute font-medium border border-dotted border-mute',
    plate: 'bg-paper px-1.5 py-0.5',
    description:
      'Insufficient evidence. The evidence needed could not be obtained. This is a ' +
      'statement about the reading, not about the package.',
  },
}

export function fieldStateLabel(state: FieldState): string {
  return PRESENTATION[state].label
}

interface FieldStateChipProps {
  state: FieldState
}

export function FieldStateChip({ state }: FieldStateChipProps) {
  const { label, Glyph, chip, plate, description } = PRESENTATION[state]
  return (
    <span className={`inline-flex items-center p-1 text-label leading-none ${chip}`}>
      <span className={`inline-flex items-center gap-2 px-1.5 py-0.5 ${plate}`}>
        <Glyph className="h-4 w-4 shrink-0" />
        <span>{label}</span>
      </span>
      <span className="sr-only">{description}</span>
    </span>
  )
}
