import React from 'react';
import type { DailyBucket } from './types';

export const TimelineBucketChart: React.FC<{ timeline: DailyBucket[] }> = ({ timeline }) => {
  const maxTotal = Math.max(
    ...timeline.map((d) => d.passCount + d.reviewCount + d.potentialViolationCount),
    1
  );

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <header className="mb-3">
        <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
          Daily Inspection Timeline
        </h2>
        <p className="text-xs text-slate-600">7-day aggregated scan verification volume</p>
      </header>

      {timeline.length === 0 ? (
        <p className="text-xs text-slate-500 py-6 text-center">No inspection scans recorded in this period.</p>
      ) : (
        <div className="space-y-2.5">
          {timeline.map((bucket) => {
            const total = bucket.passCount + bucket.reviewCount + bucket.potentialViolationCount;
            const passPct = total > 0 ? (bucket.passCount / total) * 100 : 0;
            const reviewPct = total > 0 ? (bucket.reviewCount / total) * 100 : 0;
            const violPct = total > 0 ? (bucket.potentialViolationCount / total) * 100 : 0;

            return (
              <div key={bucket.date} className="text-xs">
                <div className="flex justify-between items-center mb-1 text-slate-800 font-medium">
                  <span className="font-mono">{bucket.date}</span>
                  <span className="text-slate-600">{total} scans</span>
                </div>
                <div
                  className="h-5 w-full bg-slate-100 rounded flex overflow-hidden border border-slate-300"
                  style={{ width: `${Math.max((total / maxTotal) * 100, 20)}%` }}
                >
                  <div
                    style={{ width: `${passPct}%` }}
                    title={`PASS: ${bucket.passCount}`}
                    className="bg-emerald-400 h-full border-r border-slate-300"
                  />
                  <div
                    style={{ width: `${reviewPct}%` }}
                    title={`REVIEW: ${bucket.reviewCount}`}
                    className="bg-amber-300 h-full border-r border-slate-300"
                  />
                  <div
                    style={{ width: `${violPct}%` }}
                    title={`POTENTIAL VIOLATION: ${bucket.potentialViolationCount}`}
                    className="bg-rose-500 h-full"
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-slate-700">
          <span className="w-3 h-3 bg-emerald-400 border border-slate-400 rounded-xs"></span> PASS
        </span>
        <span className="flex items-center gap-1.5 text-slate-700">
          <span className="w-3 h-3 bg-amber-300 border border-slate-400 rounded-xs"></span> REVIEW
        </span>
        <span className="flex items-center gap-1.5 text-slate-700">
          <span className="w-3 h-3 bg-rose-500 border border-slate-900 rounded-xs"></span> POTENTIAL VIOLATION
        </span>
      </div>
    </section>
  );
};
