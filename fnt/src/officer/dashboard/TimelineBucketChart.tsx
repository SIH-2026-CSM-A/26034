import React from 'react';
import type { DailyBucket } from './types';

/** Verdict colour tokens — must match StatusPill and HeatmapJurisdiction:
 *  PASS             → emerald-500
 *  REVIEW           → amber-400
 *  POTENTIAL_VIOLATION → rose-600
 */
const CHART_COLOURS = {
  pass: 'bg-emerald-500',
  review: 'bg-amber-400',
  violation: 'bg-rose-600',
} as const;

function formatDateLabel(iso: string): string {
  try {
    const d = new Date(`${iso}T00:00:00Z`);
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric',
      month: 'short',
      timeZone: 'Asia/Kolkata',
    }).format(d);
  } catch {
    return iso.slice(5); // MM-DD fallback
  }
}

export const TimelineBucketChart: React.FC<{ timeline: DailyBucket[] }> = ({ timeline }) => {
  const maxTotal = Math.max(
    ...timeline.map((d) => d.passCount + d.reviewCount + d.potentialViolationCount),
    1
  );

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm">
      <header className="mb-4">
        <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase leading-tight">
          Daily Inspection Timeline
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">7-day aggregated scan verification volume</p>
      </header>

      {timeline.length === 0 ? (
        <p className="text-xs text-slate-500 py-8 text-center">
          No inspection scans recorded in this period.
        </p>
      ) : (
        <div className="space-y-3">
          {timeline.map((bucket) => {
            const total = bucket.passCount + bucket.reviewCount + bucket.potentialViolationCount;
            const passPct = total > 0 ? (bucket.passCount / total) * 100 : 0;
            const reviewPct = total > 0 ? (bucket.reviewCount / total) * 100 : 0;
            const violPct = total > 0 ? (bucket.potentialViolationCount / total) * 100 : 0;
            // Scale bar height/opacity by volume relative to max, so quiet days are visually quieter
            const volumeRatio = total / maxTotal;

            return (
              <div key={bucket.date} className="group">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-slate-700 tabular-nums">
                    {formatDateLabel(bucket.date)}
                  </span>
                  <span
                    className="text-xs font-bold text-slate-500 tabular-nums"
                    aria-label={`${total} total scans`}
                  >
                    {total} scan{total !== 1 ? 's' : ''}
                  </span>
                </div>
                {/* Full-width stacked bar — always spans 100%; segments show proportions */}
                <div
                  className="w-full h-6 rounded-md overflow-hidden flex bg-slate-100 border border-slate-200"
                  style={{ opacity: 0.4 + 0.6 * volumeRatio }}
                  title={`PASS: ${bucket.passCount}  REVIEW: ${bucket.reviewCount}  POTENTIAL VIOLATION: ${bucket.potentialViolationCount}`}
                >
                  {total === 0 ? (
                    <div className="w-full h-full bg-slate-100" />
                  ) : (
                    <>
                      {passPct > 0 && (
                        <div
                          className={`${CHART_COLOURS.pass} h-full`}
                          style={{ width: `${passPct}%` }}
                          aria-label={`PASS: ${bucket.passCount}`}
                        />
                      )}
                      {reviewPct > 0 && (
                        <div
                          className={`${CHART_COLOURS.review} h-full`}
                          style={{ width: `${reviewPct}%` }}
                          aria-label={`REVIEW: ${bucket.reviewCount}`}
                        />
                      )}
                      {violPct > 0 && (
                        <div
                          className={`${CHART_COLOURS.violation} h-full`}
                          style={{ width: `${violPct}%` }}
                          aria-label={`POTENTIAL VIOLATION: ${bucket.potentialViolationCount}`}
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend */}
      <div className="mt-5 pt-3 border-t border-slate-100 flex flex-wrap gap-4 text-xs">
        <span className="flex items-center gap-1.5 font-semibold text-slate-700">
          <span className={`w-3 h-3 rounded-sm shrink-0 ${CHART_COLOURS.pass}`} />
          PASS
        </span>
        <span className="flex items-center gap-1.5 font-semibold text-slate-700">
          <span className={`w-3 h-3 rounded-sm shrink-0 ${CHART_COLOURS.review}`} />
          REVIEW
        </span>
        <span className="flex items-center gap-1.5 font-semibold text-slate-700">
          <span className={`w-3 h-3 rounded-sm shrink-0 ${CHART_COLOURS.violation}`} />
          POTENTIAL VIOLATION
        </span>
      </div>
    </section>
  );
};
