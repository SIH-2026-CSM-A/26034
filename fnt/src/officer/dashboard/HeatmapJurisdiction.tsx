import React from 'react';
import type { HeatmapWard, DensityBand } from './types';

interface Props {
  wards: HeatmapWard[];
  activeCategory: string;
  selectedWard: string | null;
  onSelectWard: (wardId: string) => void;
}

/** Colour tokens for heatmap density bands — must not be changed independently of
 *  the legend rendered below the grid. */
const DENSITY_CARD: Record<DensityBand, {
  card: string;
  badge: string;
  badgeText: string;
  label: string;
  dot: string;
}> = {
  HIGH: {
    card: 'bg-rose-100 border-rose-500 text-rose-950',
    badge: 'bg-rose-600 text-white',
    badgeText: 'HIGH',
    label: 'HIGH density',
    dot: 'bg-rose-500',
  },
  MEDIUM: {
    card: 'bg-amber-50 border-amber-400 text-amber-950',
    badge: 'bg-amber-400 text-amber-950',
    badgeText: 'MED',
    label: 'MEDIUM density',
    dot: 'bg-amber-400',
  },
  LOW: {
    card: 'bg-slate-50 border-slate-300 text-slate-700',
    badge: 'bg-slate-200 text-slate-700',
    badgeText: 'LOW',
    label: 'LOW density',
    dot: 'bg-slate-400',
  },
};

export const HeatmapJurisdiction: React.FC<Props> = ({
  wards,
  activeCategory,
  selectedWard,
  onSelectWard,
}) => {
  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase leading-tight">
            Jurisdiction Heatmap
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Potential violation density by ward · scan-ID hashed assignment
          </p>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-3 shrink-0">
          {(['HIGH', 'MEDIUM', 'LOW'] as DensityBand[]).map((band) => (
            <span key={band} className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <span
                className={`w-3 h-3 rounded-sm inline-block shrink-0 ${DENSITY_CARD[band].dot}`}
              />
              {DENSITY_CARD[band].badgeText}
            </span>
          ))}
        </div>
      </header>

      {wards.length === 0 ? (
        <p className="text-xs text-slate-500 py-8 text-center">
          No jurisdiction scan activity recorded.
        </p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 sm:gap-3">
          {wards.map((ward) => {
            const isSelected = ward.wardId === selectedWard;
            const tokens = DENSITY_CARD[ward.density];
            const displayCount =
              activeCategory === 'All Categories'
                ? ward.violationCount
                : (ward.categoryBreakdown[activeCategory] ?? 0);

            return (
              <button
                key={ward.wardId}
                type="button"
                onClick={() => onSelectWard(ward.wardId)}
                aria-pressed={isSelected}
                className={[
                  'relative text-left p-3.5 rounded-xl border-2 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
                  tokens.card,
                  isSelected
                    ? 'ring-2 ring-offset-2 ring-indigo-600 shadow-md scale-[1.02]'
                    : 'hover:shadow-sm',
                ].join(' ')}
              >
                {/* Density badge */}
                <span
                  className={`absolute top-2 right-2 text-[10px] font-black tracking-widest px-1.5 py-0.5 rounded ${tokens.badge}`}
                >
                  {tokens.badgeText}
                </span>

                {/* Ward name */}
                <p className="font-bold text-xs leading-snug pr-8 mb-2">
                  {ward.wardName}
                </p>

                {/* Counts */}
                <p className="text-xs">
                  <span className="font-black text-base tabular-nums">
                    {displayCount}
                  </span>{' '}
                  <span className="opacity-70 font-medium">
                    {displayCount === 1 ? 'potential violation' : 'potential violations'}
                  </span>
                </p>
                <p className="text-xs opacity-60 mt-0.5">
                  {ward.totalScans} total scans
                </p>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
};
