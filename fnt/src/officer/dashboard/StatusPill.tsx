import React from 'react';
import type { Verdict } from './types';

/** Verdict colour tokens — consistent across every dashboard component:
 *  PASS             → emerald-500  (green, solid pill)
 *  REVIEW           → amber-400    (yellow, solid pill, dark text)
 *  POTENTIAL_VIOLATION → rose-600  (red, solid pill)
 */
export const StatusPill: React.FC<{ verdict: Verdict }> = ({ verdict }) => {
  switch (verdict) {
    case 'PASS':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold tracking-widest rounded-full bg-emerald-500 text-white shadow-sm whitespace-nowrap">
          <svg aria-hidden="true" className="w-3 h-3 shrink-0" viewBox="0 0 12 12" fill="none">
            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          PASS
        </span>
      );
    case 'REVIEW':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold tracking-widest rounded-full bg-amber-400 text-amber-950 shadow-sm whitespace-nowrap">
          <svg aria-hidden="true" className="w-3 h-3 shrink-0" viewBox="0 0 12 12" fill="none">
            <path d="M6 2v5M6 9v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          REVIEW
        </span>
      );
    case 'POTENTIAL_VIOLATION':
    case 'POTENTIAL VIOLATION':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold tracking-widest rounded-full bg-rose-600 text-white shadow-sm whitespace-nowrap">
          <svg aria-hidden="true" className="w-3 h-3 shrink-0" viewBox="0 0 12 12" fill="none">
            <path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          POTENTIAL VIOLATION
        </span>
      );
  }
};
