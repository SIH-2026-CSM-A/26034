import { SEEDED_DEMO_OFFICER } from '../../services/demo';
import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import type { components } from '../../services/generated/schema';
import { CategoryFilterBar } from './CategoryFilterBar';
import { HeatmapJurisdiction } from './HeatmapJurisdiction';
import { TimelineBucketChart } from './TimelineBucketChart';
import { ClauseBreakdownView } from './ClauseBreakdownView';
import type {
  ClauseDrilldown,
  DailyBucket,
  DashboardData,
  RecordDetail,
  WardAggregate,
} from './types';
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
  if (!cat) return 'Packaged Food';
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
  });

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const { data: scans, error: apiError } = await apiClient.GET('/scans');
      if (apiError) {
        setError('Failed to fetch scans from enforcement API.');
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
        const scanVerdict =
          detail.verdict === 'POTENTIAL_VIOLATION'
            ? 'POTENTIAL VIOLATION'
            : detail.verdict === 'PASS'
            ? 'PASS'
            : 'REVIEW';

        detail.findings.forEach((finding) => {
          const clauseRef = finding.rule_snapshot?.clause_ref || 'Rule 6(1)(a)';
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
            verdict: scanVerdict,
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
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error communicating with API.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-indigo-50 text-slate-900 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">

        {/* ── Header card ── */}
        <header className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          {/* Coloured accent bar at top */}
          <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-violet-500 to-rose-500" />

          <div className="p-4 sm:p-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  {/* Shield icon */}
                  <svg className="w-5 h-5 text-indigo-600 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z" clipRule="evenodd" />
                  </svg>
                  <h1 className="text-base sm:text-lg font-black text-slate-950 tracking-tight">
                    Legal Metrology Enforcement
                  </h1>
                </div>
                <p className="text-xs text-slate-500 pl-7">
                  SIH 2026 · PS 26034 · Rule 6 Jurisdiction Monitoring
                </p>
              </div>

              <div className="flex items-center gap-2 self-start sm:self-auto">
                <button
                  type="button"
                  onClick={loadDashboard}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 hover:border-slate-400 transition-colors disabled:opacity-50 shadow-sm"
                >
                  {loading ? (
                    <>
                      <span className="w-3 h-3 border-2 border-slate-400 border-t-slate-700 rounded-full animate-spin" />
                      Refreshing…
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <path d="M13.5 8A5.5 5.5 0 112.5 8M13.5 8V4.5M13.5 8H10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      Refresh
                    </>
                  )}
                </button>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </span>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-rose-500 shrink-0" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 3.5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 018 4.5zm0 7.5a.75.75 0 110-1.5.75.75 0 010 1.5z"/>
                  </svg>
                  <span>{error}</span>
                </div>
                <button
                  type="button"
                  onClick={loadDashboard}
                  className="shrink-0 font-bold underline hover:text-rose-950"
                >
                  Retry
                </button>
              </div>
            )}

            <CategoryFilterBar
              categories={data.categories}
              activeCategory={activeCategory}
              onSelectCategory={setActiveCategory}
            />
          </div>
        </header>

        {loading ? (
          <div className="p-16 text-center bg-white border border-slate-200 rounded-2xl shadow-sm">
            <div className="inline-flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-sm font-semibold text-slate-600">
                Loading enforcement metrics…
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 items-start">
            <div className="lg:col-span-7 space-y-4 sm:space-y-6">
              {seededCount > 0 && (
                <p className="border border-query bg-paper px-3 py-2 font-mono text-label text-query">
                  Includes {seededCount} seeded demo scan{seededCount === 1 ? '' : 's'} (officer {SEEDED_DEMO_OFFICER}), entered to populate this dashboard, not collected in the field.
                </p>
              )}
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

            <div className="lg:col-span-5">
              <ClauseBreakdownView
                clauses={data.clauses}
                activeCategory={activeCategory}
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
};

export default OfficerDashboard;
