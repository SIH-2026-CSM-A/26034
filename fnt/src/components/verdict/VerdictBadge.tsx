import React from 'react';
import { OverallVerdict, VERDICT_CONFIG } from '../../types/verdict';

export interface VerdictBadgeProps {
  readonly verdict: OverallVerdict;
  readonly size?: 'sm' | 'md' | 'lg';
  readonly showDescription?: boolean;
  readonly className?: string;
}

/**
 * VerdictBadge Component for PCCS.
 *
 * CRITICAL ACCESSIBILITY & COMPLIANCE RULE:
 * POTENTIAL VIOLATION and PASS must NEVER be distinguishable by colour alone.
 * Must remain unmistakably distinct in 100% grayscale or monochrome printouts.
 *
 * Visual Distinction Architecture:
 * 1. Text Label: Explicitly printed in bold caps ("PASS" | "REVIEW" | "POTENTIAL VIOLATION").
 * 2. Distinct Geometric Shape / Iconography:
 *    - PASS: Solid Circle icon with Checkmark (✓)
 *    - REVIEW: Warning Triangle icon with Exclamation (⚠)
 *    - POTENTIAL VIOLATION: Stop Octagon icon with Cross (✕)
 * 3. Border & Frame Geometry:
 *    - PASS: 1px continuous solid hairline border, pill/full-round geometry
 *    - REVIEW: 2px dashed/stippled warning border, medium rounded geometry
 *    - POTENTIAL VIOLATION: 2px heavy continuous solid border with inner highlight, sharp square geometry
 */
export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  showDescription = false,
  className = '',
}) => {
  const meta = VERDICT_CONFIG[verdict];

  // Size styling tokens
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1.5',
    md: 'text-sm px-3 py-1 gap-2',
    lg: 'text-base px-4 py-1.5 gap-2.5',
  }[size];

  const iconSizes = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }[size];

  // Verdict-specific styling: Shape, Border, Colors, and Typography
  const verdictStyles = {
    PASS: {
      container:
        'bg-emerald-50 text-emerald-900 border border-emerald-700 rounded-full border-solid',
      badgeFill: 'bg-emerald-700 text-white',
      symbolText: '✓',
    },
    REVIEW: {
      container:
        'bg-amber-50 text-amber-950 border-2 border-amber-600 rounded-md border-dashed',
      badgeFill: 'bg-amber-600 text-white',
      symbolText: '!',
    },
    POTENTIAL_VIOLATION: {
      container:
        'bg-rose-50 text-rose-950 border-2 border-rose-800 rounded-sm border-solid shadow-sm',
      badgeFill: 'bg-rose-800 text-white',
      symbolText: '✕',
    },
  }[verdict];

  return (
    <div className={`inline-flex flex-col ${className}`}>
      <span
        role="status"
        aria-label={meta.ariaLabel}
        className={`inline-flex items-center font-mono font-semibold tracking-wider uppercase select-none ${sizeClasses} ${verdictStyles.container}`}
      >
        {/* Grayscale-safe geometric icon indicator */}
        <span
          className={`flex items-center justify-center rounded-sm font-bold leading-none ${iconSizes} ${verdictStyles.badgeFill}`}
          aria-hidden="true"
        >
          {verdict === 'PASS' && (
            <svg
              className="w-3/4 h-3/4 stroke-current"
              viewBox="0 0 16 16"
              fill="none"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="3 8.5 6.5 12 13 4" />
            </svg>
          )}
          {verdict === 'REVIEW' && (
            <svg
              className="w-3/4 h-3/4 fill-current"
              viewBox="0 0 16 16"
            >
              <path d="M8 1.5L1 14h14L8 1.5zm0 3.5c.3 0 .5.2.5.5v4c0 .3-.2.5-.5.5s-.5-.2-.5-.5v-4c0-.3.2-.5.5-.5zm0 6.5a.75.75 0 1 1 0 1.5.75.75 0 0 1 0-1.5z" />
            </svg>
          )}
          {verdict === 'POTENTIAL_VIOLATION' && (
            <svg
              className="w-3/4 h-3/4 stroke-current"
              viewBox="0 0 16 16"
              fill="none"
              strokeWidth="2.5"
              strokeLinecap="round"
            >
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          )}
        </span>

        {/* Explicit Text Label */}
        <span className="font-bold">{meta.label}</span>
      </span>

      {showDescription && (
        <span className="text-xs text-gov-slate-600 mt-1 max-w-xs font-sans normal-case">
          {meta.description}
        </span>
      )}
    </div>
  );
};
