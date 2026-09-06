import { useId } from 'react'
import {
  CAPTURE_SIZE,
  PDP_OUTLINE,
  UNRESOLVED_REGION,
} from '../../fixtures/verdict-detail.fixture'
import type { ExtractedSpan, Point } from '../../fixtures/contracts'

/**
 * The capture, as a second register rather than a thumbnail.
 *
 * This is a drawn diagram and it says so in the frame. There is no photograph
 * to show: DAT-001 has captured two real retail samples and neither is in this
 * repository. A photo-realistic render would be fake data on a compliance
 * screen, which is not a trade this product can make. A diagram that announces
 * itself is not. When PIP-002 lands, the plate takes a capture URL and the
 * drawn panel is replaced; the polygon overlay is unchanged by that swap.
 *
 * The focused row's polygon is pinned here. Where a row cites no spans there is
 * no polygon to pin — that is the contract's shape, not a gap — and the plate
 * shows the unresolved search region instead.
 */

function toPoints(polygon: readonly Point[]): string {
  return polygon.map(([x, y]) => `${x},${y}`).join(' ')
}

interface CapturePlateProps {
  /** Spans cited by the focused row. Empty where nothing could be read. */
  pinnedSpans: readonly ExtractedSpan[]
  /** True when the focused row is the one with no readable evidence. */
  showUnresolvedRegion: boolean
  /** Named in the caption so the officer knows what the plate is of. */
  inspectionId: string
}

export function CapturePlate({
  pinnedSpans,
  showUnresolvedRegion,
  inspectionId,
}: CapturePlateProps) {
  /*
   * Both plates are in the DOM at once — one is `lg:hidden`, the other
   * `hidden lg:block` — so a fixed pattern id would give two elements the same
   * id and every `url(#...)` reference would resolve to the first, which is
   * the display:none one, and paint nothing. Scoped per instance.
   */
  const hatchId = useId()

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${CAPTURE_SIZE.width} ${CAPTURE_SIZE.height}`}
        className="block h-auto w-full border border-ink bg-paper"
        role="img"
        aria-label={
          showUnresolvedRegion
            ? `Fixture capture for ${inspectionId}. The region searched for the retail ` +
              'sale price declaration is marked as unresolved: no reference object was ' +
              'in frame, so no measurement could be taken from it.'
            : `Fixture capture for ${inspectionId}, with the focused finding's evidence ` +
              'outlined on the principal display panel.'
        }
      >
        <defs>
          {/* The same 45° hatch the INSUFFICIENT EVIDENCE chip carries, so the
              unresolved region and the row read as one statement. */}
          <pattern id={hatchId} width="16" height="16" patternUnits="userSpaceOnUse">
            {/* Drawn on the diagonal rather than rotated: a rotated tile does
                not seam cleanly at this size and the hatch reads as noise. */}
            <path
              d="M-4 4 4 -4M0 16 16 0M12 20 20 12"
              fill="none"
              stroke="#4A5560"
              strokeWidth="3"
            />
          </pattern>
        </defs>

        {/* The package. Drawn geometry, deliberately flat — this is a diagram of
            a capture, not an attempt at one. Its outline is the principal
            display panel, which is what Table-I bands its letter heights on. */}
        <rect x="0" y="0" width={CAPTURE_SIZE.width} height={CAPTURE_SIZE.height} fill="#DCDFDB" />
        <polygon points={toPoints(PDP_OUTLINE)} fill="#C9CEC9" stroke="#4A5560" strokeWidth="4" />

        {/* Declaration blocks, as ruled placeholder lines. No lettering: text
            drawn here would be text an officer could try to read. */}
        <g stroke="#A8AFAC" strokeWidth="10" strokeLinecap="butt">
          <line x1="186" y1="286" x2="800" y2="272" />
          <line x1="186" y1="330" x2="742" y2="318" />
          <line x1="186" y1="374" x2="812" y2="360" />
          <line x1="186" y1="418" x2="646" y2="406" />
          <line x1="194" y1="632" x2="690" y2="620" />
          <line x1="194" y1="748" x2="626" y2="738" />
          <line x1="186" y1="912" x2="536" y2="902" />
          <line x1="186" y1="960" x2="470" y2="950" />
        </g>

        {showUnresolvedRegion && (
          <g>
            <polygon points={toPoints(UNRESOLVED_REGION)} fill={`url(#${hatchId})`} />
            <polygon
              points={toPoints(UNRESOLVED_REGION)}
              fill="none"
              stroke="#4A5560"
              strokeWidth="5"
              strokeDasharray="3 10"
              strokeLinecap="round"
            />
          </g>
        )}

        {pinnedSpans.map((span) => (
          <polygon
            key={span.span_id}
            points={toPoints(span.polygon)}
            fill="none"
            stroke="#101A24"
            strokeWidth="6"
          />
        ))}
      </svg>

      <figcaption className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="border border-ink px-1.5 py-0.5 font-mono text-label text-ink">
          Fixture capture
        </span>
        <span className="text-secondary text-mute">
          {showUnresolvedRegion
            ? 'Hatched area: searched for the retail sale price declaration, not resolved.'
            : 'Outlined: the evidence behind the focused finding.'}
        </span>
      </figcaption>
    </figure>
  )
}
