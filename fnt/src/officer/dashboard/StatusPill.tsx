import React from 'react';
import type { Verdict } from '../../fixtures/dashboard';

export const StatusPill: React.FC<{ verdict: Verdict }> = ({ verdict }) => {
  switch (verdict) {
    case 'PASS':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-emerald-900 bg-emerald-100 border border-emerald-700 rounded">
          <span aria-hidden="true">?</span> PASS
        </span>
      );
    case 'REVIEW':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold tracking-wider text-amber-950 bg-amber-100 border-2 border-dashed border-amber-800 rounded">
          <span aria-hidden="true">?</span> REVIEW
        </span>
      );
    case 'POTENTIAL VIOLATION':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold tracking-wider text-rose-950 bg-rose-100 border-2 border-solid border-slate-950 rounded shadow-xs">
          <span aria-hidden="true">?</span> POTENTIAL VIOLATION
        </span>
      );
  }
};
