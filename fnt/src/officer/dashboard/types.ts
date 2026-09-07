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

export interface HeatmapWard {
  wardId: string;
  wardName: string;
  density: DensityBand;
  violationCount: number;
  totalScans: number;
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
  wards: HeatmapWard[];
  clauses: ClauseDrilldown[];
  timeline: DailyBucket[];
}
