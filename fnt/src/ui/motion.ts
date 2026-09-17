import type { Transition, Variants } from 'framer-motion'

/**
 * Motion tokens. Three springs and two variant sets; a component that needs a
 * fourth is asking for a job one of these already does. Springs rather than
 * durations because a spring carries the velocity of whatever interrupted it.
 *
 * Nothing here gates content: every entrance starts from opacity 0 on a node
 * that is already mounted with its final text, so a verdict is in the DOM, and
 * announced, on the frame the data arrives.
 */
export const spring = {
  /** Presses, toggles, the nav pill. Settles fast, no visible overshoot. */
  snap: { type: 'spring', stiffness: 520, damping: 38, mass: 0.7 },
  /** Cards, list rows, shared-element moves. */
  glide: { type: 'spring', stiffness: 260, damping: 30, mass: 0.9 },
  /** Hover lift on the map and tiles. A little life, never a wobble. */
  lift: { type: 'spring', stiffness: 380, damping: 24, mass: 0.6 },
} as const satisfies Record<string, Transition>

/** Parent of a staggered list. 35ms a row, capped by the children themselves. */
export const stagger: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: 0.035, delayChildren: 0.02 } },
}

/** One staggered child: rises 10px into place. */
export const rise: Variants = {
  hidden: { opacity: 0, y: 10 },
  shown: { opacity: 1, y: 0, transition: spring.glide },
}
