import React, { useId } from 'react';
import type { HeatmapWard, DensityBand } from './types';

interface Props {
  wards: HeatmapWard[];
  activeCategory: string;
  selectedWard: string | null;
  onSelectWard: (wardId: string) => void;
}

export const HeatmapJurisdiction: React.FC<Props> = ({ wards, activeCategory, selectedWard, onSelectWard }) => {
  const patternId = useId();

  const getCardStyle = (density: DensityBand, isSelected: boolean) => {
    const base = 'relative p-3.5 rounded-lg border-2 text-left transition-all';
    const selectionRing = isSelected ? 'ring-2 ring-offset-1 ring-slate-900 shadow-md' : 'shadow-xs';

    if (density === 'HIGH') {
      return `${base} ${selectionRing} border-slate-900 bg-rose-50 text-slate-950`;
    }
    if (density === 'MEDIUM') {
      return `${base} ${selectionRing} border-dashed border-slate-700 bg-amber-50 text-slate-900`;
    }
    return `${base} ${selectionRing} border-solid border-slate-300 bg-slate-50 text-slate-800`;
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <svg className="absolute w-0 h-0" aria-hidden="true">
        <defs>
          <pattern id={`${patternId}-hatch`} width="8" height="8" patternUnits="userSpaceOnUse">
            <path d="M-1,1 l2,-2 M0,8 l8,-8 M7,9 l2,-2" stroke="#475569" strokeWidth="1.2" opacity="0.35" />
          </pattern>
        </defs>
      </svg>

      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-3">
        <h2 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
          Jurisdiction Heatmap · Ward Density
        </h2>
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span className="flex items-center gap-1 font-bold text-slate-900">
            <span className="w-2.5 h-2.5 bg-rose-200 border border-slate-900 inline-block"></span> HIGH
          </span>
          <span className="flex items-center gap-1 font-semibold text-slate-800">
            <span className="w-2.5 h-2.5 bg-amber-100 border border-dashed border-slate-700 inline-block"></span> MED
          </span>
          <span className="flex items-center gap-1 text-slate-600">
            <span className="w-2.5 h-2.5 bg-slate-100 border border-slate-300 inline-block"></span> LOW
          </span>
        </div>
      </header>

      {wards.length === 0 ? (
        <p className="text-xs text-slate-500 py-6 text-center">No jurisdiction scan activity recorded.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {wards.map((ward) => {
          const isSelected = ward.wardId === selectedWard;
          const displayCount =
            activeCategory === 'All Categories'
              ? ward.violationCount
              : ward.categoryBreakdown[activeCategory] ?? 0;

          return (
            <button
              key={ward.wardId}
              type="button"
              onClick={() => onSelectWard(ward.wardId)}
              className={getCardStyle(ward.density, isSelected)}
            >
              {ward.density === 'HIGH' && (
                <div
                  className="absolute inset-0 pointer-events-none rounded-lg"
                  style={{ backgroundImage: `url(#${patternId}-hatch)` }}
                />
              )}
              <div className="relative z-10 flex items-start justify-between gap-2 mb-2">
                <span className="font-bold text-sm text-slate-900">{ward.wardName}</span>
                <span className="shrink-0 text-xs font-mono font-bold px-2 py-0.5 border border-slate-800 bg-white text-slate-900 rounded">
                  {ward.density}
                </span>
              </div>
              <div className="relative z-10 text-xs text-slate-700">
                <span className="font-bold text-slate-900">{displayCount}</span> potential violations · {ward.totalScans} total scans
              </div>
            </button>
          );
        })}
        </div>
      )}
    </section>
  );
};
