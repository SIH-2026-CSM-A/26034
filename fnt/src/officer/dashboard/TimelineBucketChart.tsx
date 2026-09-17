import { motion } from 'framer-motion';
import React, { useState } from 'react';
import { spring } from '../../ui/motion';
import { VerdictTag } from '../components/VerdictBanner';
import type { DailyBucket } from './types';

function formatDateLabel(iso: string): string {
  try {
    const d = new Date(`${iso}T00:00:00Z`);
    return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'Asia/Kolkata' }).format(d);
  } catch {
    return iso.slice(5); // MM-DD fallback
  }
}

/**
 * Stacked columns, one per day. Segment order is fixed — PASS at the foot, then REVIEW,
 * then POTENTIAL VIOLATION — and the readout above names each count beside its verdict
 * tag, so the chart never depends on telling three colours apart.
 */
const SEGMENTS = [
  { key: 'potentialViolationCount', verdict: 'POTENTIAL_VIOLATION', fill: 'bg-seal' },
  { key: 'reviewCount', verdict: 'REVIEW', fill: 'bg-query' },
  { key: 'passCount', verdict: 'PASS', fill: 'bg-attest' },
] as const;

export const TimelineBucketChart: React.FC<{ timeline: DailyBucket[] }> = ({ timeline }) => {
  const [picked, setPicked] = useState<string | null>(null);
  const totalOf = (d: DailyBucket) => d.passCount + d.reviewCount + d.potentialViolationCount;
  const maxTotal = Math.max(...timeline.map(totalOf), 1);
  const pickedDay = timeline.find((d) => d.date === picked);

  // The readout shows the picked day, or every day on the chart summed.
  const shown = SEGMENTS.map((seg) => ({
    ...seg,
    count: pickedDay ? pickedDay[seg.key] : timeline.reduce((sum, d) => sum + d[seg.key], 0),
  })).reverse();
  const hasScans = timeline.some((d) => totalOf(d) > 0);

  return (
    <section className="card p-5 sm:p-6">
      <header>
        <h2 className="text-section">Scans per day, by verdict</h2>
        <p className="mt-0.5 text-secondary text-mute" aria-live="polite">
          {pickedDay ? formatDateLabel(pickedDay.date) : 'All days shown'} · tap a day for its counts
        </p>
      </header>

      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
        {shown.map((seg) => (
          <li key={seg.key} className="flex items-center gap-2">
            <VerdictTag verdict={seg.verdict} />
            <span className="font-mono text-body font-medium">{seg.count}</span>
          </li>
        ))}
      </ul>

      {!hasScans ? (
        <p className="mt-6 text-secondary text-mute">No inspection scans recorded in this period.</p>
      ) : (
        <div className="-mx-2 mt-5 overflow-x-auto px-2 [scrollbar-width:thin]">
          <div className="flex h-44 min-w-full items-stretch gap-1.5" style={{ width: `max(100%, ${timeline.length * 44}px)` }}>
            {timeline.map((bucket, i) => {
              const total = totalOf(bucket);
              const active = bucket.date === picked;
              return (
                <button
                  key={bucket.date}
                  type="button"
                  aria-pressed={active}
                  aria-label={`${formatDateLabel(bucket.date)}: ${total} scan${total === 1 ? '' : 's'}. PASS ${bucket.passCount}, REVIEW ${bucket.reviewCount}, POTENTIAL VIOLATION ${bucket.potentialViolationCount}`}
                  onClick={() => setPicked(active ? null : bucket.date)}
                  className={`group flex min-w-[38px] flex-1 flex-col items-center justify-end gap-1 rounded-ctl px-1 pb-1 pt-2 transition-colors duration-base ${
                    active ? 'bg-ink/[0.06]' : 'hover:bg-ink/[0.03]'
                  }`}
                >
                  <span className="font-mono text-label text-mute">{total}</span>
                  <span className="flex min-h-0 w-full flex-1 items-end justify-center">
                  <motion.span
                    className="flex w-full max-w-[36px] origin-bottom flex-col gap-0.5 overflow-hidden rounded-md"
                    style={{ height: `${(total / maxTotal) * 100}%`, minHeight: total > 0 ? 6 : 2 }}
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    transition={{ ...spring.glide, delay: Math.min(i, 14) * 0.03 }}
                  >
                    {total === 0 ? (
                      <span className="h-full w-full bg-hairline" />
                    ) : (
                      SEGMENTS.map(
                        (seg) =>
                          bucket[seg.key] > 0 && (
                            <span key={seg.key} className={`w-full ${seg.fill}`} style={{ flexGrow: bucket[seg.key] }} />
                          ),
                      )
                    )}
                  </motion.span>
                  </span>
                  <span className="whitespace-nowrap text-[11px] text-mute">{formatDateLabel(bucket.date)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
};
