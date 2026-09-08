import React, { useId } from 'react';
import type { HeatmapWard, DensityBand } from './types';

interface Props {
  wards: HeatmapWard[];
  activeCategory: string;
  selectedWard: string | null;
  onSelectWard: (wardId: string) => void;
}

/**
 * Fill, stroke and legend copy per density band. The three fills are the scale; a
 * reader sees the band from the tile before reading a number. Kept in one table so the
 * legend and the tiles cannot drift apart.
 */
const BAND: Record<DensityBand, { fill: string; stroke: string; text: string; label: string }> = {
  HIGH: { fill: '#A32A1E', stroke: '#6E1A12', text: '#FFFFFF', label: 'High' },
  MEDIUM: { fill: '#E0A126', stroke: '#845605', text: '#101A24', label: 'Medium' },
  LOW: { fill: '#8FC7A8', stroke: '#14603C', text: '#101A24', label: 'Low' },
};

const ORDER: DensityBand[] = ['HIGH', 'MEDIUM', 'LOW'];

// Tile geometry in SVG units. Three columns; the viewBox grows with the row count, and
// the SVG scales to its container, so the same drawing reads at 390px and at 1280px.
const COLS = 3;
const TILE = 100;
const GAP = 8;

export const HeatmapJurisdiction: React.FC<Props> = ({
  wards,
  activeCategory,
  selectedWard,
  onSelectWard,
}) => {
  // Scoped: the dashboard renders this once per breakpoint variant, and a duplicate
  // pattern id resolves url(#…) to the hidden copy and paints nothing.
  const hatchId = useId();
  const rows = Math.max(1, Math.ceil(wards.length / COLS));
  const width = COLS * TILE + (COLS - 1) * GAP;
  const height = rows * TILE + (rows - 1) * GAP;

  const countFor = (ward: HeatmapWard) =>
    activeCategory === 'All Categories'
      ? ward.violationCount
      : (ward.categoryBreakdown[activeCategory] ?? 0);

  return (
    <section className="border border-hairline bg-paper p-4 sm:p-5">
      <header className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-label font-bold uppercase tracking-wider text-ink">
            Jurisdiction heatmap
          </h2>
          <p className="mt-0.5 text-secondary text-mute">
            Potential-violation density by ward
          </p>
        </div>
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-label="Density scale">
          {ORDER.map((band) => (
            <li key={band} className="flex items-center gap-1.5 text-label text-ink">
              <span
                aria-hidden="true"
                className="inline-block h-3.5 w-3.5 shrink-0"
                style={{ backgroundColor: BAND[band].fill, border: `1px solid ${BAND[band].stroke}` }}
              />
              {BAND[band].label}
            </li>
          ))}
        </ul>
      </header>

      {wards.length === 0 ? (
        <p className="py-8 text-center text-secondary text-mute">
          No jurisdiction scan activity recorded.
        </p>
      ) : (
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="block w-full"
          role="group"
          aria-label="Ward density map"
        >
          <defs>
            <pattern id={hatchId} width="6" height="6" patternUnits="userSpaceOnUse">
              <path d="M-1 1 1 -1M0 6 6 0M5 7 7 5" stroke="#101A24" strokeWidth="1" strokeOpacity="0.25" />
            </pattern>
          </defs>
          {wards.map((ward, i) => {
            const x = (i % COLS) * (TILE + GAP);
            const y = Math.floor(i / COLS) * (TILE + GAP);
            const band = BAND[ward.density];
            const selected = ward.wardId === selectedWard;
            const count = countFor(ward);
            const [wardCode, ...rest] = ward.wardName.split(' - ');
            const locality = rest.join(' - ');
            return (
              <g
                key={ward.wardId}
                transform={`translate(${x} ${y})`}
                role="button"
                tabIndex={0}
                aria-pressed={selected}
                aria-label={`${ward.wardName}: ${count} potential violation${count === 1 ? '' : 's'} in ${ward.totalScans} scans, ${band.label} density`}
                onClick={() => onSelectWard(ward.wardId)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectWard(ward.wardId);
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                <rect width={TILE} height={TILE} rx="4" fill={band.fill} stroke={band.stroke} strokeWidth={selected ? 4 : 1.5} />
                {ward.totalScans === 0 && (
                  <rect width={TILE} height={TILE} rx="4" fill={`url(#${hatchId})`} />
                )}
                <text x="8" y="18" fontFamily="IBM Plex Mono, ui-monospace, monospace" fontSize="10" fontWeight="600" fill={band.text}>
                  {wardCode}
                </text>
                <text x="8" y="31" fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize="9" fill={band.text} fillOpacity="0.9">
                  {locality.length > 18 ? `${locality.slice(0, 17)}…` : locality}
                </text>
                <text x="8" y="72" fontFamily="IBM Plex Mono, ui-monospace, monospace" fontSize="30" fontWeight="600" fill={band.text}>
                  {count}
                </text>
                <text x="8" y="90" fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize="9" fill={band.text} fillOpacity="0.9">
                  of {ward.totalScans} scan{ward.totalScans === 1 ? '' : 's'}
                </text>
                {selected && (
                  <rect x="2" y="2" width={TILE - 4} height={TILE - 4} rx="3" fill="none" stroke="#101A24" strokeWidth="1.5" strokeDasharray="3 2" />
                )}
              </g>
            );
          })}
        </svg>
      )}

      <p className="mt-3 border-t border-hairline pt-2 text-label text-mute">
        Ward assignment is a scan-ID hash over placeholder ward names. The geography is not
        verified and must not be read as where a scan was taken.
      </p>
    </section>
  );
};
