import type { components } from '../../services/generated/schema';

export type Verdict = components['schemas']['Verdict'];

/**
 * How many scans this page loads, and the number the map's footnote states.
 *
 * 200 is the API's own maximum for `GET /scans`. It was the default page size of 50, and
 * that was a defect a visitor hit rather than a tuning choice: the database held 33
 * ward-bearing scans and 10 potential violations among them, and **not one of them was in
 * the newest fifty** — thirty of those fifty were a timing run submitted with no ward. So
 * all 145 wards rendered unshaded while the data sat one page behind the window.
 *
 * Declared here and read by both the fetch and the footnote, so the page cannot request one
 * window and tell an officer it is showing another. If the API's maximum ever rises past
 * this, the honest fix is paging, not a larger literal: a window that silently drops the
 * oldest scan is the defect this constant exists to stop being invisible.
 */
export const SCAN_WINDOW = 200;

export interface RecordDetail {
  id: string;
  timestamp: string;
  category: string;
  clause: string;
  /** Null when the scan carries no verdict. Never defaulted to one. */
  verdict: Verdict | null;
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
  /** Counts over the scans this page loaded. `noVerdict` is scans still processing, refused or failed. */
  totals: { scans: number; pass: number; review: number; potentialViolation: number; noVerdict: number };
}
