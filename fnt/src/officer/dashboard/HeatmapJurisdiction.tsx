import React, { useId, useMemo, useState } from 'react';
import type { WardAggregate, DensityBand } from './types';
import { GHMC_WARDS, GHMC_VIEWBOX } from './ghmcWards';

interface Props {
  wards: WardAggregate[];
  activeCategory: string;
  selectedWard: string | null;
  onSelectWard: (wardName: string) => void;
  unassignedScans: number;
  unknownWardScans: number;
}

/**
 * Fill, stroke and legend copy per density band, plus the "no scans" state. The three
 * bands are the choropleth scale; a reader sees the band from the polygon before reading
 * a number. Kept in one table so the legend and the map cannot drift apart. `NONE` is a
 * neutral pale fill for a ward with no scans in this dataset — deliberately not the LOW
 * green, because "no scans recorded" is not "low violations".
 */
const BAND: Record<DensityBand | 'NONE', { fill: string; stroke: string; label: string }> = {
  HIGH: { fill: '#A32A1E', stroke: '#6E1A12', label: 'High' },
  MEDIUM: { fill: '#E0A126', stroke: '#845605', label: 'Medium' },
  LOW: { fill: '#8FC7A8', stroke: '#14603C', label: 'Low' },
  NONE: { fill: '#D0D4CF', stroke: '#A8AFAC', label: 'No scans' },
};

const LEGEND: ReadonlyArray<DensityBand | 'NONE'> = ['HIGH', 'MEDIUM', 'LOW', 'NONE'];

/**
 * Map each distinct count to a relative band by ranking the distinct values into thirds:
 * the lowest third of *values* is LOW, the highest third HIGH, the rest MEDIUM. Ranking
 * distinct values (not raw samples) is what a choropleth wants — it does not collapse the
 * middle band just because many wards happen to share the same count — and it guarantees
 * all three bands appear whenever there are three or more distinct counts, which is the
 * spread the demonstration seed is built to produce. Computed over the wards that carry a
 * scan in the active category, so the shade a polygon shows always matches its tooltip.
 */
function densityBands(counts: number[]): Map<number, DensityBand> {
  const result = new Map<number, DensityBand>();
  const distinct = Array.from(new Set(counts)).sort((a, b) => a - b);
  const n = distinct.length;
  if (n === 0) return result;
  if (n === 1) {
    const only = distinct[0] ?? 0;
    result.set(only, only > 10 ? 'HIGH' : only > 0 ? 'MEDIUM' : 'LOW');
    return result;
  }
  if (n === 2) {
    result.set(distinct[0] ?? 0, 'LOW');
    result.set(distinct[1] ?? 0, 'HIGH');
    return result;
  }
  const cut = Math.max(1, Math.floor(n / 3));
  distinct.forEach((count, i) => {
    if (i < cut) result.set(count, 'LOW');
    else if (i >= n - cut) result.set(count, 'HIGH');
    else result.set(count, 'MEDIUM');
  });
  return result;
}

export const HeatmapJurisdiction: React.FC<Props> = ({
  wards,
  activeCategory,
  selectedWard,
  onSelectWard,
  unassignedScans,
  unknownWardScans,
}) => {
  const titleId = useId();
  const [hovered, setHovered] = useState<string | null>(null);

  // Aggregate by ward name, and the count shown for the active category. Density bands
  // are computed only over wards that carry a scan, so a ward with no activity does not
  // pull the terciles down — it is simply "no scans".
  const { byName, bands } = useMemo(() => {
    const byName = new Map<string, WardAggregate>();
    for (const w of wards) byName.set(w.name, w);
    const countFor = (w: WardAggregate) =>
      activeCategory === 'All Categories'
        ? w.violationCount
        : (w.categoryBreakdown[activeCategory] ?? 0);
    const bands = densityBands(wards.map(countFor));
    return { byName, bands };
  }, [wards, activeCategory]);

  const countFor = (w: WardAggregate) =>
    activeCategory === 'All Categories'
      ? w.violationCount
      : (w.categoryBreakdown[activeCategory] ?? 0);

  const readout = hovered ?? selectedWard;
  const readoutAgg = readout ? byName.get(readout) : undefined;

  return (
    <section className="border border-hairline bg-paper p-4 sm:p-5">
      <header className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 id={titleId} className="text-label font-bold uppercase tracking-wider text-ink">
            Where scans were submitted
          </h2>
          <p className="mt-0.5 text-secondary text-mute">
            Greater Hyderabad ward boundaries, shaded by potential-violation density in this
            dataset
          </p>
        </div>
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-label="Density scale">
          {LEGEND.map((band) => (
            <li key={band} className="flex items-center gap-1.5 text-label text-ink">
              <span
                aria-hidden="true"
                className="inline-block h-3.5 w-3.5 shrink-0 rounded-sm"
                style={{ backgroundColor: BAND[band].fill, border: `1px solid ${BAND[band].stroke}` }}
              />
              {BAND[band].label}
            </li>
          ))}
        </ul>
      </header>

      {/* Live readout: the hovered ward, or the selected one when nothing is hovered.
          This is the tap target's answer on touch, where there is no hover. */}
      <p
        className="mb-2 min-h-[1.5rem] text-label text-ink"
        aria-live="polite"
      >
        {readout ? (
          readoutAgg ? (
            <span>
              <span className="font-mono font-semibold">{readout}</span>
              {' — '}
              {countFor(readoutAgg)} potential violation{countFor(readoutAgg) === 1 ? '' : 's'} in{' '}
              {readoutAgg.totalScans} scan{readoutAgg.totalScans === 1 ? '' : 's'}
            </span>
          ) : (
            <span>
              <span className="font-mono font-semibold">{readout}</span> — no scans recorded
            </span>
          )
        ) : (
          <span className="text-mute">Tap or hover a ward for its counts.</span>
        )}
      </p>

      <svg
        viewBox={`0 0 ${GHMC_VIEWBOX.width} ${GHMC_VIEWBOX.height}`}
        className="block h-auto w-full touch-manipulation"
        role="group"
        aria-labelledby={titleId}
        style={{ maxHeight: '70vh' }}
      >
        {GHMC_WARDS.map((geo) => {
          const agg = byName.get(geo.name);
          const count = agg ? countFor(agg) : 0;
          const key: DensityBand | 'NONE' = agg ? (bands.get(count) ?? 'LOW') : 'NONE';
          const band = BAND[key];
          const selected = geo.name === selectedWard;
          const active = selected || geo.name === hovered;
          return (
            <path
              key={geo.num}
              d={geo.d}
              fill={band.fill}
              stroke={active ? '#101A24' : band.stroke}
              strokeWidth={active ? 3 : 0.6}
              vectorEffect="non-scaling-stroke"
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={
                agg
                  ? `${geo.name}: ${count} potential violation${count === 1 ? '' : 's'} in ${agg.totalScans} scan${agg.totalScans === 1 ? '' : 's'}, ${band.label} density`
                  : `${geo.name}: no scans recorded`
              }
              className="cursor-pointer outline-none focus-visible:stroke-ink"
              style={{ transition: 'stroke-width 80ms' }}
              onPointerEnter={() => setHovered(geo.name)}
              onPointerLeave={() => setHovered((h) => (h === geo.name ? null : h))}
              onClick={() => onSelectWard(geo.name)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectWard(geo.name);
                }
              }}
            />
          );
        })}
      </svg>

      <div className="mt-3 space-y-1 border-t border-hairline pt-2 text-label text-mute">
        <p>
          Boundaries are the real GHMC wards (145 of 150), from OpenStreetMap via DataMeet,
          ODbL. Shading shows where scans in <em>this dataset</em> were submitted and how many
          reached POTENTIAL VIOLATION — it is not a survey of Hyderabad, and a shaded ward is
          not a verified enforcement finding.
        </p>
        {(unassignedScans > 0 || unknownWardScans > 0) && (
          <p>
            {unassignedScans > 0 && (
              <span>
                {unassignedScans} scan{unassignedScans === 1 ? '' : 's'} recorded no ward
                {unknownWardScans > 0 ? '; ' : '.'}
              </span>
            )}
            {unknownWardScans > 0 && (
              <span>
                {unknownWardScans} name a ward outside GHMC. Neither is shaded on the map.
              </span>
            )}
          </p>
        )}
      </div>
    </section>
  );
};
