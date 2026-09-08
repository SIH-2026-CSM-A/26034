import type { components } from '../../services/generated/schema';

export type Verdict = components['schemas']['Verdict'] | 'POTENTIAL VIOLATION';
export type DensityBand = 'HIGH' | 'MEDIUM' | 'LOW';

export interface RecordDetail {
  id: string;
  timestamp: string;
  category: string;
  clause: string;
  verdict: Verdict;
  storeName: string;
  jurisdictionWard: string;
}

export interface WardAggregate {
  /** Canonical GHMC ward label, matching a `name` in `ghmcWards.ts` and the value
   * persisted on the scan. */
  name: string;
  violationCount: number;
  totalScans: number;
  /** Potential-violation counts split by display category, for the category filter. */
  categoryBreakdown: Record<string, number>;
}

export interface ClauseDrilldown {
  clauseNumber: string;
  description: string;
  potentialViolationRate: number; // percentage (0-100)
  sampleSize: number;
  category: string;
  records: RecordDetail[];
}

export interface DailyBucket {
  date: string;
  category: string;
  passCount: number;
  reviewCount: number;
  potentialViolationCount: number;
}

export interface DashboardData {
  categories: string[];
  /** One entry per GHMC ward that has at least one scan. Wards with no scans are absent
   * here and render as "no scans" on the map, never as a low-density finding. */
  wards: WardAggregate[];
  /** Scans carrying no ward (older records, or the officer named none). Reported as a
   * count beside the map, never shaded onto a polygon. */
  unassignedScans: number;
  /** Scans whose recorded ward matches no GHMC ward in `ghmcWards.ts`. */
  unknownWardScans: number;
  clauses: ClauseDrilldown[];
  timeline: DailyBucket[];
}
