import { useCallback, useEffect, useRef, useState } from 'react'

/** Where the officer says the principal display panel is, in the photograph's own pixels. */
export interface PanelMark {
  x: number
  y: number
  width: number
  height: number
}

/** A drag shorter than this on either side is a tap, and a tap is not a panel. */
const MIN_MARK_PX = 8

interface Props {
  src: string
  alt: string
  mark: PanelMark | null
  onChange: (mark: PanelMark | null) => void
  disabled?: boolean
  /** Sizes the drag surface; the photograph is letterboxed inside it. */
  className?: string
  /** The caption and clear button under the surface; a host with its own omits them. */
  caption?: boolean
}

/**
 * One drag over the photograph marks the principal display panel.
 *
 * Rule 7(2) Table-I bands the required character height by the panel's area, and no
 * detector is configured that can say where the panel is, so the officer states it —
 * the same confirmation the system already asks for before any enforcement act. The
 * mark is optional: without it the scan runs and Table-I reports that the area was not
 * measured. Its area in cm² is measured by the server through the reference object;
 * nothing here knows a millimetre.
 *
 * Pointer events, so one finger on a phone and a mouse on a desk are the same gesture.
 * The image is `object-contain` inside the surface, so its rendered rectangle is
 * computed rather than assumed to be the element's box.
 */
export function PanelMarker({
  src,
  alt,
  mark,
  onChange,
  disabled = false,
  className = '',
  caption = true,
}: Props) {
  const imgRef = useRef<HTMLImageElement | null>(null)
  const startRef = useRef<{ x: number; y: number } | null>(null)
  const [draft, setDraft] = useState<PanelMark | null>(null)
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null)
  // The overlay is laid out from the photograph's on-screen rectangle, which moves when
  // the viewport does; a resize re-renders so it is read again.
  const [, setViewport] = useState(0)
  useEffect(() => {
    const onResize = () => setViewport((n) => n + 1)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  /** The photograph's rectangle on screen, and the scale from screen to image pixels. */
  const geometry = useCallback(() => {
    const img = imgRef.current
    if (!img || !natural) return null
    const box = img.getBoundingClientRect()
    const scale = Math.min(box.width / natural.w, box.height / natural.h)
    const width = natural.w * scale
    const height = natural.h * scale
    return {
      left: box.left + (box.width - width) / 2,
      top: box.top + (box.height - height) / 2,
      width,
      height,
      scale,
    }
  }, [natural])

  const toImage = useCallback(
    (e: React.PointerEvent) => {
      const g = geometry()
      if (!g || !natural) return null
      const x = Math.round(Math.min(Math.max((e.clientX - g.left) / g.scale, 0), natural.w))
      const y = Math.round(Math.min(Math.max((e.clientY - g.top) / g.scale, 0), natural.h))
      return { x, y }
    },
    [geometry, natural],
  )

  const rectangle = (a: { x: number; y: number }, b: { x: number; y: number }): PanelMark => ({
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(a.x - b.x),
    height: Math.abs(a.y - b.y),
  })

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (disabled || e.button !== 0) return
    const p = toImage(e)
    if (!p) return
    e.currentTarget.setPointerCapture(e.pointerId)
    startRef.current = p
    setDraft(rectangle(p, p))
  }

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!startRef.current) return
    const p = toImage(e)
    if (p) setDraft(rectangle(startRef.current, p))
  }

  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const start = startRef.current
    startRef.current = null
    setDraft(null)
    const p = toImage(e)
    if (!start || !p) return
    const next = rectangle(start, p)
    // A tap keeps whatever was marked before; clearing is its own button.
    if (next.width >= MIN_MARK_PX && next.height >= MIN_MARK_PX) onChange(next)
  }

  const shown = draft ?? mark
  const g = geometry()
  // The overlay is positioned against the surface, so the photograph's offset inside it is
  // added back; the surface and the image share an origin only when nothing is letterboxed.
  const surface = imgRef.current?.getBoundingClientRect()
  const overlay =
    shown && g && natural && surface
      ? {
          left: g.left - surface.left + (shown.x / natural.w) * g.width,
          top: g.top - surface.top + (shown.y / natural.h) * g.height,
          width: (shown.width / natural.w) * g.width,
          height: (shown.height / natural.h) * g.height,
        }
      : null

  const surfaceElement = (
    <div
      role="img"
      aria-label={`${alt}. Drag over the principal display panel to mark it.`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className={`relative select-none overflow-hidden rounded-card bg-ink ${
        disabled ? 'cursor-not-allowed' : 'cursor-crosshair'
      } ${className}`}
      style={{
        touchAction: 'none',
        ...(className || !natural
          ? {}
          : { width: '100%', aspectRatio: `${natural.w} / ${natural.h}` }),
      }}
    >
      <img
        ref={imgRef}
        src={src}
        alt=""
        draggable={false}
        onLoad={(e) =>
          setNatural({
            w: e.currentTarget.naturalWidth,
            h: e.currentTarget.naturalHeight,
          })
        }
        className="pointer-events-none h-full w-full object-contain"
      />
      {overlay && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute border-2 border-accent bg-accent/15 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"
          style={overlay}
        />
      )}
    </div>
  )
  if (!caption) return surfaceElement

  return (
    <div className="space-y-3">
      {surfaceElement}
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p className="font-mono text-label text-mute">
          {mark
            ? `Panel marked: ${mark.width} × ${mark.height} px at (${mark.x}, ${mark.y})`
            : 'No panel marked — drag a rectangle over the principal display panel'}
        </p>
        {mark && (
          <button
            type="button"
            onClick={() => onChange(null)}
            disabled={disabled}
            className="btn btn-quiet min-h-[44px]"
          >
            Clear mark
          </button>
        )}
      </div>
      <p className="text-secondary text-mute">
        The mark states where the principal display panel is; it selects the Rule 7(2) Table-I band
        for the required character height. Its area in cm² is measured through the reference object
        when the scan runs and is stated on the Table-I finding. Optional: without a mark, Table-I
        reports that the panel area was not measured.
      </p>
    </div>
  )
}
