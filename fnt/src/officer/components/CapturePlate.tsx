import type { ExtractedSpan } from '../../fixtures/contracts'

interface CapturePlateProps {
  /** Spans cited by the focused row. Empty where nothing could be read. */
  pinnedSpans: readonly ExtractedSpan[]
  /** True when the focused row is the one with no readable evidence. */
  showUnresolvedRegion: boolean
  /** Named in the caption so the officer knows what the plate is of. */
  inspectionId: string
}

export function CapturePlate(_props: CapturePlateProps) {
  // Capture geometry is not available in the API response.
  // We do not render fabricated geometries on a compliance tool.
  return null
}
