import { animate, useInView, useReducedMotion } from 'framer-motion'
import { useEffect, useRef } from 'react'

/**
 * A number that counts up to its value when it scrolls into view. The real value
 * is what React renders and what assistive technology reads; the count is painted
 * over it afterwards, so a failed animation leaves the right number on screen.
 */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const reduced = useReducedMotion()

  useEffect(() => {
    const node = ref.current
    if (!node || !inView || reduced) return
    const controls = animate(0, value, {
      duration: 0.9,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => {
        node.textContent = Math.round(v).toLocaleString('en-IN')
      },
    })
    return () => {
      controls.stop()
      node.textContent = value.toLocaleString('en-IN')
    }
  }, [value, inView, reduced])

  return (
    <span ref={ref} className={`tabular ${className ?? ''}`}>
      {value.toLocaleString('en-IN')}
    </span>
  )
}
