import { SEEDED_DEMO_OFFICER } from '../../services/demo';
import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { serverMessage } from '../../services/errors';
import type { components } from '../../services/generated/schema';
import { motion } from 'framer-motion';
import { CountUp } from '../../ui/CountUp';
import { rise, spring, stagger } from '../../ui/motion';
import { Notice } from '../../ui/Notice';
import { OfficerHeader } from '../components/OfficerHeader';
import { VerdictTag } from '../components/VerdictBanner';
import { CategoryFilterBar } from './CategoryFilterBar';
import { HeatmapJurisdiction } from './HeatmapJurisdiction';
import { TimelineBucketChart } from './TimelineBucketChart';
import { ClauseBreakdownView } from './ClauseBreakdownView';
import type {
  ClauseDrilldown,
  DailyBucket,
  DashboardData,
  RecordDetail,
  Verdict,
  WardAggregate,
} from './types';
import { SCAN_WINDOW } from './types';
import { GHMC_WARDS } from './ghmcWards';

type ScanSummary = components['schemas']['ScanSummary'];
type ScanDetail = components['schemas']['ScanDetail'];

// The real GHMC ward labels the map can shade. A scan whose recorded ward is not one of
// these is counted as "unknown" and shaded nowhere, never quietly dropped.
const GHMC_WARD_NAMES: ReadonlySet<string> = new Set(GHMC_WARDS.map((w) => w.name));

const STANDARD_CLAUSES: ReadonlyArray<{ clauseNumber: string; description: string; category: string }> = [
  {
    clauseNumber: 'Rule 6(1)(a)',
    description: 'Name and complete address of manufacturer / packer absent or incomplete',
    category: 'Packaged Food',
  },
  {
    clauseNumber: 'Rule 6(1)(d)',
    description: 'Net quantity declaration numeral height or unit symbol specification requirement',
    category: 'Packaged Food',
  },
  {
    clauseNumber: 'Rule 6(1)(f)',
    description: 'Retail sale price (MRP) declaration obscured, smudged, or missing taxes notice',
    category: 'Beverages',
  },
  {
    clauseNumber: 'Rule 6(1)(e)',
    description: 'Month and year of manufacture or packaging missing',
    category: 'Personal Care',
  },
  {
    clauseNumber: 'Rule 6(1)(b)',
    description: 'Generic or common name of commodity not conspicuously stated',
    category: 'Household Goods',
  },
];

function formatCategory(cat?: string | null): string {
  // No category on the scan is its own answer. Filing it under a real one would move counts.
  if (!cat) return 'Uncategorised';
  const lower = cat.toLowerCase();
  if (lower === 'food') return 'Packaged Food';
  if (lower === 'cosmetics') return 'Personal Care';
  if (lower === 'beverages') return 'Beverages';
  if (lower === 'medical_device') return 'Personal Care';
  if (lower === 'household_goods') return 'Household Goods';
  return cat.charAt(0).toUpperCase() + cat.slice(1);
}

function formatTimestamp(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    }).format(new Date(iso)) + ' IST';
  } catch {
    return iso;
  }
}

export const OfficerDashboard: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<string>('All Categories');
  const [selectedWard, setSelectedWard] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [seededCount, setSeededCount] = useState<number>(0);
  const [data, setData] = useState<DashboardData>({
    categories: ['All Categories', 'Packaged Food', 'Personal Care', 'Beverages', 'Household Goods'],
    wards: [],
    unassignedScans: 0,
    unknownWardScans: 0,
    clauses: [],
    timeline: [],
    totals: { scans: 0, pass: 0, review: 0, potentialViolation: 0, noVerdict: 0 },
  });
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const { data: scans, error: apiError, response } = await apiClient.GET('/scans', {
        params: { query: { limit: SCAN_WINDOW } },
      });
      if (apiError) {
        setError(serverMessage(apiError, response));
        setLoading(false);
        return;
      }

      const scanList: ScanSummary[] = scans ?? [];
      setSeededCount(scanList.filter((s) => s.officer_id === SEEDED_DEMO_OFFICER).length);

      // Fetch detailed findings for up to 30 scans
      const detailsMap = new Map<string, ScanDetail>();
      const detailBatches = scanList.slice(0, 30);
      const detailResults = await Promise.allSettled(
        detailBatches.map((s) =>
          apiClient.GET('/scans/{scan_id}', { params: { path: { scan_id: s.id } } })
        )
      );

      detailResults.forEach((res) => {
        if (res.status === 'fulfilled' && res.value.data) {
          detailsMap.set(res.value.data.id, res.value.data);
        }
      });

      // Categories
      const foundCategories = new Set<string>();
      scanList.forEach((s) => {
        if (s.product_category) {
          foundCategories.add(formatCategory(s.product_category));
        }
      });
      const defaultCategories = ['Packaged Food', 'Personal Care', 'Beverages', 'Household Goods'];
      const combinedCategories = [
        'All Categories',
        ...Array.from(new Set([...defaultCategories, ...foundCategories])),
      ];

      // Ward aggregation, keyed by the ward the officer actually recorded on the scan.
      // A ward is created in the map only when a scan names it, so wards with no activity
      // stay off the aggregate and render as "no scans" rather than a low-density finding.
      // A scan with no ward, or one naming a ward the map does not know, is counted aside
      // and shaded nowhere. Density bands are computed in the map component, over the
      // active category, so the shading always matches the number shown.
      const wardMap = new Map<string, WardAggregate>();
      let unassignedScans = 0;
      let unknownWardScans = 0;

      scanList.forEach((scan) => {
        const wardName = scan.ward?.trim();
        if (!wardName) {
          unassignedScans += 1;
          return;
        }
        if (!GHMC_WARD_NAMES.has(wardName)) {
          unknownWardScans += 1;
          return;
        }
        let ward = wardMap.get(wardName);
        if (!ward) {
          ward = { name: wardName, violationCount: 0, totalScans: 0, categoryBreakdown: {} };
          wardMap.set(wardName, ward);
        }
        ward.totalScans += 1;
        if (scan.verdict === 'POTENTIAL_VIOLATION') {
          ward.violationCount += 1;
          const category = formatCategory(scan.product_category);
          ward.categoryBreakdown[category] = (ward.categoryBreakdown[category] ?? 0) + 1;
        }
      });

      const wardArray = Array.from(wardMap.values());

      // Timeline 7-day buckets
      const timelineBucketsMap = new Map<string, DailyBucket>();
      const now = new Date();
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const key = d.toISOString().slice(0, 10);
        timelineBucketsMap.set(key, {
          date: key,
          category: 'All Categories',
          passCount: 0,
          reviewCount: 0,
          potentialViolationCount: 0,
        });
      }

      scanList.forEach((scan) => {
        const dateKey = scan.created_at.slice(0, 10);
        let bucket = timelineBucketsMap.get(dateKey);
        if (!bucket) {
          bucket = {
            date: dateKey,
            category: 'All Categories',
            passCount: 0,
            reviewCount: 0,
            potentialViolationCount: 0,
          };
          timelineBucketsMap.set(dateKey, bucket);
        }

        if (scan.verdict === 'PASS') {
          bucket.passCount += 1;
        } else if (scan.verdict === 'REVIEW') {
          bucket.reviewCount += 1;
        } else if (scan.verdict === 'POTENTIAL_VIOLATION') {
          bucket.potentialViolationCount += 1;
        }
      });

      const timeline = Array.from(timelineBucketsMap.values()).sort((a, b) =>
        a.date.localeCompare(b.date)
      );

      // Clause Drilldown aggregation
      const clauseMap = new Map<string, ClauseDrilldown>();
      STANDARD_CLAUSES.forEach((sc) => {
        clauseMap.set(sc.clauseNumber, {
          clauseNumber: sc.clauseNumber,
          description: sc.description,
          potentialViolationRate: 0,
          sampleSize: 0,
          category: sc.category,
          records: [],
        });
      });

      // Populate from live scan details findings
      detailsMap.forEach((detail) => {
        const assignedWard = detail.ward?.trim() || 'Unassigned';
        const category = formatCategory(detail.product_category);

        detail.findings.forEach((finding) => {
          // A finding with no clause on its snapshot is grouped as exactly that, never under a real rule.
          const clauseRef = finding.rule_snapshot?.clause_ref || 'No clause recorded';
          let clause = clauseMap.get(clauseRef);
          if (!clause) {
            clause = {
              clauseNumber: clauseRef,
              description: finding.rule_snapshot?.source_text || finding.reason,
              potentialViolationRate: 0,
              sampleSize: 0,
              category,
              records: [],
            };
            clauseMap.set(clauseRef, clause);
          }

          clause.sampleSize += 1;
          const isIssue = finding.state === 'FAIL' || finding.state === 'REVIEW_REQUIRED';

          const record: RecordDetail = {
            id: detail.subject_ref || `SCAN-${detail.id.slice(0, 8).toUpperCase()}`,
            timestamp: formatTimestamp(detail.created_at),
            category,
            clause: clauseRef,
            verdict: detail.verdict ?? null,
            storeName:
              detail.source_type === 'catalogue_record'
                ? 'E-Commerce Marketplace Listing'
                : 'Physical Retail Package Inspection',
            jurisdictionWard: assignedWard,
          };

          if (isIssue) {
            clause.records.push(record);
          }
        });
      });

      // Recalculate potential violation rates
      clauseMap.forEach((c) => {
        if (c.sampleSize > 0) {
          c.potentialViolationRate = Number(
            ((c.records.length / c.sampleSize) * 100).toFixed(1)
          );
        }
      });

      const clauses = Array.from(clauseMap.values());

      setData({
        categories: combinedCategories,
        wards: wardArray,
        unassignedScans,
        unknownWardScans,
        clauses,
        timeline,
        totals: {
          scans: scanList.length,
          pass: scanList.filter((s) => s.verdict === 'PASS').length,
          review: scanList.filter((s) => s.verdict === 'REVIEW').length,
          potentialViolation: scanList.filter((s) => s.verdict === 'POTENTIAL_VIOLATION').length,
          noVerdict: scanList.filter((s) => !s.verdict).length,
        },
      });
      setLoadedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error communicating with API.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const tiles: ReadonlyArray<{ label: string; value: number; verdict?: Verdict }> = [
    { label: 'Scans loaded', value: data.totals.scans },
    { label: 'PASS', value: data.totals.pass, verdict: 'PASS' },
    { label: 'REVIEW', value: data.totals.review, verdict: 'REVIEW' },
    { label: 'POTENTIAL VIOLATION', value: data.totals.potentialViolation, verdict: 'POTENTIAL_VIOLATION' },
    ...(data.totals.noVerdict > 0 ? [{ label: 'No verdict issued', value: data.totals.noVerdict }] : []),
  ];

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="Dashboard" />
      <main className="mx-auto max-w-[1280px] px-4 pb-28 pt-6 md:pb-16 md:pt-10">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div>
            <h1 className="text-title">Legal Metrology enforcement</h1>
            <p className="mt-1 text-secondary text-mute">SIH 2026 · PS 26034 · Rule 6 jurisdiction monitoring</p>
          </div>
          <div className="flex items-center gap-3">
            {/* When the numbers were read, not a claim that they are streaming. */}
            {loadedAt && !loading && (
              <span className="font-mono text-label text-mute">
                Loaded {loadedAt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })}
              </span>
            )}
            <button type="button" onClick={loadDashboard} disabled={loading} className="btn btn-quiet w-[132px] px-4">
              <svg
                className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`}
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path d="M13.5 8A5.5 5.5 0 112.5 8M13.5 8V4.5M13.5 8H10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              {loading ? 'Refreshing' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className="mt-5">
          <CategoryFilterBar
            categories={data.categories}
            activeCategory={activeCategory}
            onSelectCategory={setActiveCategory}
          />
        </div>

        {error && (
          <div className="mt-6">
            <Notice
              title="Unable to load the dashboard"
              role="alert"
              action={
                <button type="button" onClick={loadDashboard} className="btn btn-quiet">
                  Retry
                </button>
              }
            >
              {error}
            </Notice>
          </div>
        )}

        {loading ? (
          <DashboardSkeleton />
        ) : (
          !error && (
            <>
              <motion.ul
                variants={stagger}
                initial="hidden"
                animate="shown"
                className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-[repeat(auto-fit,minmax(0,1fr))] lg:grid-flow-col"
              >
                {tiles.map((tile, i) => (
                  <motion.li
                    key={tile.label}
                    variants={rise}
                    whileHover={{ y: -3 }}
                    transition={spring.lift}
                    className={`card flex min-h-[120px] flex-col justify-between p-4 sm:p-5 ${i === 0 || tile.verdict === 'POTENTIAL_VIOLATION' ? 'col-span-2 lg:col-span-1' : ''}`}
                  >
                    {tile.verdict ? (
                      <span className="self-start">
                        <VerdictTag verdict={tile.verdict} />
                      </span>
                    ) : (
                      <span className="text-label text-mute">{tile.label}</span>
                    )}
                    <CountUp value={tile.value} className="font-display text-display" />
                  </motion.li>
                ))}
              </motion.ul>

              {seededCount > 0 && (
                <p className="badge-seeded mt-4 rounded-ctl px-3 py-2 text-label">
                  Includes {seededCount} seeded demo scan{seededCount === 1 ? '' : 's'} (officer {SEEDED_DEMO_OFFICER}), entered to populate this dashboard, not collected in the field.
                </p>
              )}

              <div className="mt-6 grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
                <div className="space-y-6 lg:col-span-8">
                  <HeatmapJurisdiction
                    wards={data.wards}
                    activeCategory={activeCategory}
                    selectedWard={selectedWard}
                    onSelectWard={(name) => setSelectedWard(name === selectedWard ? null : name)}
                    unassignedScans={data.unassignedScans}
                    unknownWardScans={data.unknownWardScans}
                  />
                  <TimelineBucketChart timeline={data.timeline} />
                </div>
                <div className="lg:col-span-4">
                  <ClauseBreakdownView clauses={data.clauses} activeCategory={activeCategory} />
                </div>
              </div>
            </>
          )
        )}
      </main>
    </div>
  );
};

/** The loaded page's boxes, empty: tile row, map card, side card. Nothing moves when data lands. */
function DashboardSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading enforcement metrics">
      <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`card flex min-h-[120px] flex-col justify-between p-4 sm:p-5 ${i === 0 || i === 3 ? 'col-span-2 lg:col-span-1' : ''}`}>
            <span className="skeleton h-6 w-24 rounded-full" />
            <span className="skeleton h-10 w-16" />
          </div>
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="card p-6 lg:col-span-8">
          <span className="skeleton block h-6 w-56" />
          <span className="skeleton mt-2 block h-4 w-72 max-w-full" />
          <span className="skeleton mt-6 block aspect-[1000/807] w-full rounded-card" />
        </div>
        <div className="card space-y-3 p-6 lg:col-span-4">
          <span className="skeleton block h-6 w-44" />
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className="skeleton block h-[84px] w-full rounded-ctl" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default OfficerDashboard;
