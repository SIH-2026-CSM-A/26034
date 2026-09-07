import React, { useState } from 'react';
import type { ClauseDrilldown, RecordDetail } from '../../fixtures/dashboard';
import { StatusPill } from './StatusPill';

interface Props {
  clauses: ClauseDrilldown[];
  activeCategory: string;
}

export const ClauseBreakdownView: React.FC<Props> = ({ clauses, activeCategory }) => {
  const [activeClause, setActiveClause] = useState<ClauseDrilldown | null>(null);

  const filteredClauses =
    activeCategory === 'All Categories'
      ? clauses
      : clauses.filter((c) => c.category === activeCategory);

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <header className="mb-3">
        <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
          Violation Rate by Rule Clause
        </h2>
        <p className="text-xs text-slate-600">Select any clause to inspect underlying shop records</p>
      </header>

      <div className="space-y-2">
        {filteredClauses.map((clause) => (
          <button
            key={clause.clauseNumber}
            type="button"
            onClick={() => setActiveClause(clause)}
            className="w-full text-left p-3 rounded-lg border border-slate-300 hover:border-slate-800 bg-slate-50 hover:bg-white transition-all group"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="font-bold text-sm text-slate-900 group-hover:underline">
                {clause.clauseNumber}
              </span>
              <span className="text-xs font-mono font-bold text-rose-900 bg-rose-100 px-2 py-0.5 rounded border border-rose-300">
                {clause.potentialViolationRate}% rate
              </span>
            </div>
            <p className="text-xs text-slate-600 line-clamp-1 mb-2">{clause.description}</p>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden border border-slate-300">
              <div
                className="bg-slate-800 h-full rounded-full"
                style={{ width: `${Math.min(clause.potentialViolationRate * 2.5, 100)}%` }}
              />
            </div>
          </button>
        ))}

        {filteredClauses.length === 0 && (
          <p className="text-xs text-slate-500 py-4 text-center">No clauses recorded for this category.</p>
        )}
      </div>

      {activeClause && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4"
        >
          <div className="bg-white w-full sm:max-w-2xl max-h-[85vh] rounded-t-2xl sm:rounded-xl shadow-2xl flex flex-col border border-slate-300">
            <header className="p-4 border-b border-slate-200 flex items-start justify-between">
              <div>
                <h3 className="font-bold text-base text-slate-950">{activeClause.clauseNumber}</h3>
                <p className="text-xs text-slate-600 mt-0.5">{activeClause.description}</p>
              </div>
              <button
                type="button"
                onClick={() => setActiveClause(null)}
                className="p-1 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 text-lg font-bold leading-none"
              >
                ?
              </button>
            </header>

            <div className="p-4 overflow-y-auto space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Associated Scan Records ({activeClause.records.length})
              </h4>
              {activeClause.records.map((rec: RecordDetail) => (
                <article
                  key={rec.id}
                  className="p-3 rounded-lg border border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs font-bold text-slate-900">{rec.id}</span>
                      <span className="text-xs text-slate-500">{rec.timestamp}</span>
                    </div>
                    <div className="font-medium text-xs text-slate-800">{rec.storeName}</div>
                    <div className="text-xs text-slate-600">{rec.jurisdictionWard}</div>
                  </div>
                  <div className="shrink-0 self-start sm:self-center">
                    <StatusPill verdict={rec.verdict} />
                  </div>
                </article>
              ))}

              {activeClause.records.length === 0 && (
                <p className="text-xs text-slate-500 py-3">No active records require officer review for this clause.</p>
              )}
            </div>

            <footer className="p-3 border-t border-slate-200 bg-slate-50 flex justify-end rounded-b-xl">
              <button
                type="button"
                onClick={() => setActiveClause(null)}
                className="px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-md hover:bg-slate-800"
              >
                Close Drill-down
              </button>
            </footer>
          </div>
        </div>
      )}
    </section>
  );
};
