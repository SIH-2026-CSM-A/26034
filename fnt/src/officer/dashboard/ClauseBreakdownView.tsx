import { AnimatePresence, motion } from 'framer-motion';
import React, { useState } from 'react';
import { rise, spring, stagger } from '../../ui/motion';
import { VerdictTag } from '../components/VerdictBanner';
import type { ClauseDrilldown, RecordDetail } from './types';

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
    <section className="card flex h-full flex-col p-5 sm:p-6">
      <header className="mb-4 shrink-0">
        <h2 className="text-section">Rule clause breakdown</h2>
        <p className="mt-0.5 text-secondary text-mute">Select any clause to inspect underlying scan records</p>
      </header>

      <motion.div
        key={activeCategory}
        variants={stagger}
        initial="hidden"
        animate="shown"
        className="min-h-0 flex-1 space-y-2"
      >
        {filteredClauses.map((clause) => (
          <motion.button
            key={clause.clauseNumber}
            variants={rise}
            type="button"
            onClick={() => setActiveClause(clause)}
            className="card-lift block w-full rounded-ctl border border-hairline/70 bg-paper/60 p-3.5 text-left active:scale-[0.985]"
          >
            <span className="flex items-start justify-between gap-3">
              <span className="font-mono text-secondary font-medium text-ink">{clause.clauseNumber}</span>
              <span className="shrink-0 font-mono text-label text-mute">
                {clause.sampleSize === 0
                  ? 'no findings'
                  : `${clause.records.length} of ${clause.sampleSize} · ${clause.potentialViolationRate}%`}
              </span>
            </span>
            <span className="mt-1 line-clamp-2 block text-label font-normal text-mute">{clause.description}</span>
            {/* One neutral bar. The rate is not a verdict, so it borrows no state colour. */}
            <span className="mt-2.5 block h-1.5 w-full overflow-hidden rounded-full bg-sunken">
              <motion.span
                className="block h-full origin-left rounded-full bg-ink/70"
                style={{ width: `${Math.min(clause.potentialViolationRate, 100)}%` }}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={spring.glide}
                aria-label={`Findings needing attention: ${clause.potentialViolationRate}%`}
              />
            </span>
          </motion.button>
        ))}

        {filteredClauses.length === 0 && (
          <p className="py-6 text-secondary text-mute">No clauses recorded for this category.</p>
        )}
      </motion.div>

      {/* Drilldown: a bottom sheet on a phone, a centred card from sm. */}
      <AnimatePresence>
        {activeClause && (
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 backdrop-blur-sm sm:items-center sm:p-4"
            onClick={(e) => {
              if (e.target === e.currentTarget) setActiveClause(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setActiveClause(null);
            }}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={`Scan records for ${activeClause.clauseNumber}`}
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={spring.glide}
              className="flex max-h-[88vh] w-full flex-col rounded-t-sheet bg-surface shadow-e3 sm:max-h-[80vh] sm:max-w-2xl sm:rounded-sheet"
            >
              <header className="flex shrink-0 items-start justify-between gap-3 border-b border-hairline/70 p-5">
                <div className="min-w-0">
                  <h3 className="font-mono text-body font-medium text-ink">{activeClause.clauseNumber}</h3>
                  <p className="mt-1 text-secondary text-mute">{activeClause.description}</p>
                  <p className="mt-1 font-mono text-label text-mute">
                    {activeClause.records.length} of {activeClause.sampleSize} findings need attention ·{' '}
                    {activeClause.potentialViolationRate}%
                  </p>
                </div>
                <button
                  type="button"
                  autoFocus
                  aria-label="Close dialog"
                  onClick={() => setActiveClause(null)}
                  className="btn btn-ghost h-12 w-12 shrink-0 rounded-full px-0"
                >
                  <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </button>
              </header>

              <div className="flex-1 space-y-2.5 overflow-y-auto p-5">
                <h4 className="text-label text-mute">
                  Associated scan records <span className="font-mono text-ink">({activeClause.records.length})</span>
                </h4>
                {activeClause.records.map((rec: RecordDetail) => (
                  <article
                    key={rec.id}
                    className="flex flex-col justify-between gap-2 rounded-ctl border border-hairline/70 bg-paper/60 p-3.5 sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-x-2">
                        <span className="font-mono text-label font-semibold text-ink">{rec.id}</span>
                        <span className="font-mono text-label text-mute">{rec.timestamp}</span>
                      </div>
                      <p className="truncate text-secondary text-ink">{rec.storeName}</p>
                      <p className="truncate text-label text-mute">{rec.jurisdictionWard}</p>
                    </div>
                    <div className="shrink-0 self-start sm:self-center">
                      {rec.verdict ? (
                        <VerdictTag verdict={rec.verdict} />
                      ) : (
                        <span className="rounded-full border border-dotted border-mute px-2.5 py-1 font-mono text-label text-mute">
                          NO VERDICT
                        </span>
                      )}
                    </div>
                  </article>
                ))}

                {activeClause.records.length === 0 && (
                  <p className="py-4 text-secondary text-mute">
                    No active records require officer review for this clause.
                  </p>
                )}
              </div>

              <footer className="shrink-0 border-t border-hairline/70 px-5 py-3 pb-[max(12px,env(safe-area-inset-bottom))]">
                <p className="text-label text-mute">Ward shown is the one recorded on the scan.</p>
              </footer>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};
