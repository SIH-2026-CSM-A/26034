import { AnimatePresence, motion } from 'framer-motion';
import React, { useId, useMemo, useState } from 'react';
import { spring } from '../../ui/motion';
import type { WardAggregate } from './types';
import { SCAN_WINDOW } from './types';
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
 * A point on the continuous ramp, 0..1, as a CSS colour. The four stops are theme
 * tokens (--c-heat-0..3 in index.css), mixed in oklab by the browser, so the map
 * follows light and dark without this component knowing which is showing — and a
 * change of category is a CSS transition between two colours, not a repaint.
 */
function heat(t: number): string {
  const scaled = Math.min(Math.max(t, 0), 1) * 3;
  const lower = Math.min(Math.floor(scaled), 2);
  const share = Math.round((scaled - lower) * 100);
  return `color-mix(in oklab, rgb(var(--c-heat-${lower})) ${100 - share}%, rgb(var(--c-heat-${lower + 1})))`;
}

const RAMP_CSS = `linear-gradient(90deg in oklab, rgb(var(--c-heat-0)), rgb(var(--c-heat-1)), rgb(var(--c-heat-2)), rgb(var(--c-heat-3)))`;

/** How many wards the ranked list shows. A display limit, not a statistic. */
const RANKED_ROWS = 6;

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

  // The count a ward shows for the active category, the largest such count (the top of
  // the ramp), and the wards ranked by it. A ward with no scans is absent from `byName`
  // and is drawn as "no scans", which is not the same thing as a count of zero.
  const { byName, countOf, max, ranked } = useMemo(() => {
    const countOf = (w: WardAggregate) =>
      activeCategory === 'All Categories' ? w.violationCount : (w.categoryBreakdown[activeCategory] ?? 0);
    const byName = new Map<string, WardAggregate>();
    for (const w of wards) byName.set(w.name, w);
    const max = wards.reduce((m, w) => Math.max(m, countOf(w)), 0);
    const ranked = wards
      .filter((w) => countOf(w) > 0)
      .sort((a, b) => countOf(b) - countOf(a) || a.name.localeCompare(b.name))
      .slice(0, RANKED_ROWS);
    return { byName, countOf, max, ranked };
  }, [wards, activeCategory]);

  const readout = hovered ?? selectedWard;
  const readoutAgg = readout ? byName.get(readout) : undefined;
  const readoutGeo = readout ? GHMC_WARDS.find((g) => g.name === readout) : undefined;
  const markerAt = readoutAgg && max > 0 ? countOf(readoutAgg) / max : null;
  const breakdown = readoutAgg
    ? Object.entries(readoutAgg.categoryBreakdown).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <section className="card overflow-hidden">
      <header className="flex flex-col gap-4 p-5 pb-3 sm:flex-row sm:items-start sm:justify-between sm:p-6 sm:pb-3">
        <div>
          <h2 id={titleId} className="text-section">
            Where scans were submitted
          </h2>
          <p className="mt-0.5 text-secondary text-mute">
            Greater Hyderabad ward boundaries, shaded by potential-violation density in this
            dataset
          </p>
        </div>

        {/* The legend is the ramp itself. The marker rides to the ward being read. */}
        <div className="w-full shrink-0 sm:w-56" aria-label="Density scale">
          <div className="relative h-3 rounded-full shadow-[inset_0_0_0_1px_rgb(var(--c-ink)/0.12)]" style={{ backgroundImage: RAMP_CSS }}>
            <AnimatePresence>
              {markerAt !== null && (
                <motion.span
                  aria-hidden="true"
                  initial={{ opacity: 0, left: `${markerAt * 100}%` }}
                  animate={{ opacity: 1, left: `${markerAt * 100}%` }}
                  exit={{ opacity: 0 }}
                  transition={spring.lift}
                  className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-surface bg-ink shadow-e2"
                />
              )}
            </AnimatePresence>
          </div>
          <div className="mt-1.5 flex items-center justify-between font-mono text-label text-mute">
            <span>0</span>
            <span>{max}</span>
          </div>
          <p className="text-label text-mute">Potential violations per ward</p>
          <p className="mt-1.5 flex items-center gap-1.5 text-label text-mute">
            <span aria-hidden="true" className="inline-block h-3 w-3 shrink-0 rounded-[3px] border border-hairline bg-sunken" />
            No scans recorded
          </p>
        </div>
      </header>

      <div className="grid gap-x-6 lg:grid-cols-[minmax(0,1fr)_260px]">
        <div className="relative px-2 sm:px-4">
          {/* Live readout: the hovered ward, or the selected one when nothing is hovered.
              This is the tap target's answer on touch, where there is no hover. It is
              always mounted at a fixed height, so reading a ward never moves the map. */}
          <p
            aria-live="polite"
            className="glass pointer-events-none absolute left-4 top-1 z-10 flex min-h-[44px] max-w-[calc(100%-2rem)] flex-col justify-center rounded-ctl border border-hairline/60 px-3 py-1.5 text-label sm:left-6"
          >
            {readout ? (
              <>
                <span className="font-mono font-semibold text-ink">
                  {readout}
                  {readoutGeo && <span className="font-normal text-mute"> · {readoutGeo.zone} zone</span>}
                </span>
                <span className="text-ink">
                  {readoutAgg
                    ? `${countOf(readoutAgg)} potential violation${countOf(readoutAgg) === 1 ? '' : 's'} in ${readoutAgg.totalScans} scan${readoutAgg.totalScans === 1 ? '' : 's'}`
                    : 'no scans recorded'}
                </span>
              </>
            ) : (
              <span className="text-mute">Tap or hover a ward for its counts.</span>
            )}
          </p>

          <motion.svg
            viewBox={`0 0 ${GHMC_VIEWBOX.width} ${GHMC_VIEWBOX.height}`}
            className="block h-auto w-full touch-manipulation overflow-visible"
            role="group"
            aria-labelledby={titleId}
            style={{ maxHeight: '70vh' }}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={spring.glide}
          >
            {GHMC_WARDS.map((geo) => {
              const agg = byName.get(geo.name);
              const count = agg ? countOf(agg) : 0;
              const selected = geo.name === selectedWard;
              return (
                <path
                  key={geo.num}
                  d={geo.d}
                  vectorEffect="non-scaling-stroke"
                  role="button"
                  tabIndex={0}
                  aria-pressed={selected}
                  aria-label={
                    agg
                      ? `${geo.name}: ${count} potential violation${count === 1 ? '' : 's'} in ${agg.totalScans} scan${agg.totalScans === 1 ? '' : 's'}`
                      : `${geo.name}: no scans recorded`
                  }
                  className={`cursor-pointer outline-none [transition:fill_600ms_cubic-bezier(0.22,1,0.36,1)] focus-visible:stroke-accent focus-visible:[stroke-width:3] ${
                    agg ? 'stroke-ink/25' : 'fill-sunken stroke-hairline'
                  }`}
                  style={agg ? { fill: heat(max > 0 ? count / max : 0) } : undefined}
                  strokeWidth={0.6}
                  onPointerEnter={() => setHovered(geo.name)}
                  onPointerLeave={() => setHovered((h) => (h === geo.name ? null : h))}
                  onFocus={() => setHovered(geo.name)}
                  onBlur={() => setHovered((h) => (h === geo.name ? null : h))}
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

            {/* The lifted ward, redrawn on top so it can rise above its neighbours — SVG has
                no z-index. Pointer events stay with the path underneath. */}
            <AnimatePresence>
              {readoutGeo && (
                <motion.path
                  key={readoutGeo.num}
                  d={readoutGeo.d}
                  vectorEffect="non-scaling-stroke"
                  aria-hidden="true"
                  pointerEvents="none"
                  className={`stroke-ink [transform-box:fill-box] [transform-origin:center] ${readoutAgg ? '' : 'fill-sunken'}`}
                  style={{
                    fill: readoutAgg ? heat(max > 0 ? countOf(readoutAgg) / max : 0) : undefined,
                    filter: 'drop-shadow(0 6px 10px rgb(var(--c-shadow) / 0.45))',
                  }}
                  strokeWidth={2}
                  initial={{ scale: 1, opacity: 0 }}
                  animate={{ scale: 1.12, opacity: 1 }}
                  exit={{ scale: 1, opacity: 0, transition: { duration: 0.12 } }}
                  transition={spring.lift}
                />
              )}
            </AnimatePresence>
          </motion.svg>
        </div>

        <div className="border-t border-hairline/70 p-5 lg:border-l lg:border-t-0 lg:py-2 lg:pl-6 lg:pr-6">
          <h3 className="text-label text-mute">Most potential violations, by ward</h3>
          {ranked.length === 0 ? (
            <p className="mt-2 text-secondary text-mute">
              No ward has a potential violation{activeCategory === 'All Categories' ? '' : ` in ${activeCategory}`} in this dataset.
            </p>
          ) : (
            <ol className="mt-2 space-y-1">
              {ranked.map((w) => {
                const active = w.name === readout;
                return (
                  <li key={w.name}>
                    <button
                      type="button"
                      aria-pressed={w.name === selectedWard}
                      onClick={() => onSelectWard(w.name)}
                      onPointerEnter={() => setHovered(w.name)}
                      onPointerLeave={() => setHovered((h) => (h === w.name ? null : h))}
                      className={`block min-h-target w-full rounded-ctl px-2.5 py-1.5 text-left transition-colors duration-base ${active ? 'bg-ink/[0.06]' : ''}`}
                    >
                      <span className="flex items-baseline justify-between gap-2 text-label">
                        <span className="truncate text-ink">{w.name}</span>
                        <span className="font-mono text-ink">{countOf(w)}</span>
                      </span>
                      <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-sunken">
                        <motion.span
                          className="block h-full origin-left rounded-full"
                          style={{ width: `${(countOf(w) / max) * 100}%`, background: heat(countOf(w) / max) }}
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: 1 }}
                          transition={spring.glide}
                        />
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}

          {readoutAgg && breakdown.length > 0 && (
            <div className="mt-4 border-t border-hairline/70 pt-3">
              <h3 className="text-label text-mute">{readout}, by category</h3>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {breakdown.map(([category, n]) => (
                  <li key={category} className="rounded-full border border-hairline bg-surface px-2.5 py-1 text-label">
                    {category} <span className="font-mono">{n}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-1 border-t border-hairline/70 bg-sunken/40 px-5 py-4 text-label text-mute sm:px-6">
        <p>
          Boundaries are the real GHMC wards (145 of 150), from OpenStreetMap via DataMeet,
          ODbL. Shading shows where the <strong>newest {SCAN_WINDOW} scans</strong> were
          submitted and how many of them reached POTENTIAL VIOLATION. A scan older than that
          window is not on this map — it is not a survey of Hyderabad, and a shaded ward is
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
