import React, { useState } from 'react';
import type { ClauseDrilldown, RecordDetail } from './types';
import { StatusPill } from './StatusPill';

interface Props {
  clauses: ClauseDrilldown[];
  activeCategory: string;
}

/** Rate badge colour — changes at thresholds so severity is immediately visible */
function rateBadgeClass(rate: number): string {
  if (rate >= 50) return 'bg-rose-100 text-rose-800 border border-rose-300';
  if (rate >= 20) return 'bg-amber-100 text-amber-800 border border-amber-300';
  return 'bg-slate-100 text-slate-700 border border-slate-300';
}

/** Progress bar fill — mirrors the rate badge palette */
function rateBarClass(rate: number): string {
  if (rate >= 50) return 'bg-rose-500';
  if (rate >= 20) return 'bg-amber-400';
  return 'bg-emerald-500';
}

export const ClauseBreakdownView: React.FC<Props> = ({ clauses, activeCategory }) => {
  const [activeClause, setActiveClause] = useState<ClauseDrilldown | null>(null);

  const filteredClauses =
    activeCategory === 'All Categories'
      ? clauses
      : clauses.filter((c) => c.category === activeCategory);

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm h-full flex flex-col">
      <header className="mb-4 shrink-0">
        <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase leading-tight">
          Rule Clause Breakdown
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Select any clause to inspect underlying scan records
        </p>
      </header>

      <div className="space-y-2 flex-1 overflow-y-auto min-h-0 -mr-1 pr-1">
        {filteredClauses.map((clause) => (
          <button
            key={clause.clauseNumber}
            type="button"
            onClick={() => setActiveClause(clause)}
            className="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-indigo-400 bg-slate-50 hover:bg-white transition-all duration-150 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <span className="font-bold text-xs text-slate-900 group-hover:text-indigo-700 transition-colors leading-snug">
                {clause.clauseNumber}
              </span>
              <span
                className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full tabular-nums ${rateBadgeClass(clause.potentialViolationRate)}`}
              >
                {clause.potentialViolationRate}%
              </span>
            </div>
            <p className="text-xs text-slate-500 line-clamp-2 mb-2 leading-relaxed">
              {clause.description}
            </p>
            {/* Progress bar — full width, fill shows rate relative to 100% */}
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${rateBarClass(clause.potentialViolationRate)}`}
                style={{ width: `${Math.min(clause.potentialViolationRate, 100)}%` }}
                aria-label={`Potential violation rate: ${clause.potentialViolationRate}%`}
              />
            </div>
          </button>
        ))}

        {filteredClauses.length === 0 && (
          <p className="text-xs text-slate-500 py-8 text-center">
            No clauses recorded for this category.
          </p>
        )}
      </div>

      {/* Drilldown modal */}
      {activeClause && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Scan records for ${activeClause.clauseNumber}`}
          className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setActiveClause(null); }}
        >
          <div className="bg-white w-full sm:max-w-2xl max-h-[90vh] sm:max-h-[80vh] rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col border border-slate-200">
            {/* Modal header */}
            <header className="p-4 sm:p-5 border-b border-slate-200 flex items-start justify-between gap-3 shrink-0">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-0.5">
                  <h3 className="font-black text-base text-slate-950">
                    {activeClause.clauseNumber}
                  </h3>
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded-full tabular-nums ${rateBadgeClass(activeClause.potentialViolationRate)}`}
                  >
                    {activeClause.potentialViolationRate}% rate
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {activeClause.description}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close dialog"
                onClick={() => setActiveClause(null)}
                className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                  <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            </header>

            {/* Modal body */}
            <div className="p-4 sm:p-5 overflow-y-auto space-y-2.5 flex-1">
              <h4 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">
                Associated Scan Records
                <span className="ml-1.5 font-black text-slate-900">
                  ({activeClause.records.length})
                </span>
              </h4>
              {activeClause.records.map((rec: RecordDetail) => (
                <article
                  key={rec.id}
                  className="p-3 rounded-xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <span className="font-mono text-xs font-bold text-slate-900 shrink-0">
                        {rec.id}
                      </span>
                      <span className="text-xs text-slate-500 shrink-0">{rec.timestamp}</span>
                    </div>
                    <p className="font-medium text-xs text-slate-700 truncate">{rec.storeName}</p>
                    <p className="text-xs text-slate-500 truncate">{rec.jurisdictionWard}</p>
                  </div>
                  <div className="shrink-0 self-start sm:self-center">
                    <StatusPill verdict={rec.verdict} />
                  </div>
                </article>
              ))}

              {activeClause.records.length === 0 && (
                <p className="text-xs text-slate-500 py-4 text-center">
                  No active records require officer review for this clause.
                </p>
              )}
            </div>

            {/* Modal footer */}
            <footer className="p-3 sm:p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between rounded-b-2xl shrink-0">
              <p className="text-xs text-slate-400 italic">
                Scan-ID hashed ward assignment · not verified geography
              </p>
              <button
                type="button"
                onClick={() => setActiveClause(null)}
                className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Close
              </button>
            </footer>
          </div>
        </div>
      )}
    </section>
  );
};
