export type Verdict = 'PASS' | 'REVIEW' | 'POTENTIAL VIOLATION';
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

export const mockDashboardData: DashboardData = {
  categories: ['All Categories', 'Packaged Food', 'Personal Care', 'Beverages', 'Household Goods'],
  wards: [
    {
      wardId: 'W-01',
      wardName: 'Ward 12 - Begumpet',
      density: 'HIGH',
      violationCount: 42,
      totalScans: 110,
      categoryBreakdown: { 'Packaged Food': 25, 'Personal Care': 8, 'Beverages': 5, 'Household Goods': 4 },
    },
    {
      wardId: 'W-02',
      wardName: 'Ward 08 - Ameerpet',
      density: 'MEDIUM',
      violationCount: 18,
      totalScans: 85,
      categoryBreakdown: { 'Packaged Food': 10, 'Personal Care': 3, 'Beverages': 3, 'Household Goods': 2 },
    },
    {
      wardId: 'W-03',
      wardName: 'Ward 14 - Banjara Hills',
      density: 'LOW',
      violationCount: 4,
      totalScans: 90,
      categoryBreakdown: { 'Packaged Food': 2, 'Personal Care': 1, 'Beverages': 1, 'Household Goods': 0 },
    },
    {
      wardId: 'W-04',
      wardName: 'Ward 03 - Secunderabad',
      density: 'HIGH',
      violationCount: 37,
      totalScans: 95,
      categoryBreakdown: { 'Packaged Food': 20, 'Personal Care': 7, 'Beverages': 6, 'Household Goods': 4 },
    },
    {
      wardId: 'W-05',
      wardName: 'Ward 19 - Jubilee Hills',
      density: 'LOW',
      violationCount: 6,
      totalScans: 82,
      categoryBreakdown: { 'Packaged Food': 3, 'Personal Care': 1, 'Beverages': 2, 'Household Goods': 0 },
    },
    {
      wardId: 'W-06',
      wardName: 'Ward 05 - Kukatpally',
      density: 'MEDIUM',
      violationCount: 22,
      totalScans: 104,
      categoryBreakdown: { 'Packaged Food': 12, 'Personal Care': 4, 'Beverages': 4, 'Household Goods': 2 },
    },
  ],
  clauses: [
    {
      clauseNumber: 'Rule 6(1)(a)',
      description: 'Name and complete address of manufacturer / packer absent or incomplete',
      potentialViolationRate: 28.4,
      sampleSize: 148,
      category: 'Packaged Food',
      records: [
        {
          id: 'REC-2026-001',
          timestamp: '2026-09-07 10:14 IST',
          category: 'Packaged Food',
          clause: 'Rule 6(1)(a)',
          verdict: 'POTENTIAL VIOLATION',
          storeName: 'Sri Balaji Kirana & General Store',
          jurisdictionWard: 'Ward 12 - Begumpet',
        },
        {
          id: 'REC-2026-002',
          timestamp: '2026-09-07 11:20 IST',
          category: 'Packaged Food',
          clause: 'Rule 6(1)(a)',
          verdict: 'REVIEW',
          storeName: 'Lakshmi Provisions',
          jurisdictionWard: 'Ward 08 - Ameerpet',
        },
        {
          id: 'REC-2026-003',
          timestamp: '2026-09-06 16:45 IST',
          category: 'Packaged Food',
          clause: 'Rule 6(1)(a)',
          verdict: 'POTENTIAL VIOLATION',
          storeName: 'Metro Super Store',
          jurisdictionWard: 'Ward 03 - Secunderabad',
        },
      ],
    },
    {
      clauseNumber: 'Rule 6(1)(d)',
      description: 'Net quantity declaration font size or unit symbol non-compliant',
      potentialViolationRate: 19.2,
      sampleSize: 148,
      category: 'Packaged Food',
      records: [
        {
          id: 'REC-2026-004',
          timestamp: '2026-09-07 09:30 IST',
          category: 'Packaged Food',
          clause: 'Rule 6(1)(d)',
          verdict: 'POTENTIAL VIOLATION',
          storeName: 'Venkata Sai Traders',
          jurisdictionWard: 'Ward 12 - Begumpet',
        },
        {
          id: 'REC-2026-005',
          timestamp: '2026-09-06 14:10 IST',
          category: 'Packaged Food',
          clause: 'Rule 6(1)(d)',
          verdict: 'REVIEW',
          storeName: 'Sai Ram Daily Mart',
          jurisdictionWard: 'Ward 05 - Kukatpally',
        },
      ],
    },
    {
      clauseNumber: 'Rule 6(1)(f)',
      description: 'Retail sale price (MRP) declaration obscured, smudged, or missing taxes notice',
      potentialViolationRate: 15.5,
      sampleSize: 120,
      category: 'Beverages',
      records: [
        {
          id: 'REC-2026-006',
          timestamp: '2026-09-07 14:02 IST',
          category: 'Beverages',
          clause: 'Rule 6(1)(f)',
          verdict: 'POTENTIAL VIOLATION',
          storeName: 'Balaji Cold Drinks & Sweets',
          jurisdictionWard: 'Ward 03 - Secunderabad',
        },
      ],
    },
    {
      clauseNumber: 'Rule 6(1)(e)',
      description: 'Month and year of manufacture or packaging missing',
      potentialViolationRate: 11.0,
      sampleSize: 95,
      category: 'Personal Care',
      records: [
        {
          id: 'REC-2026-007',
          timestamp: '2026-09-05 17:15 IST',
          category: 'Personal Care',
          clause: 'Rule 6(1)(e)',
          verdict: 'POTENTIAL VIOLATION',
          storeName: 'Radha Medical & General',
          jurisdictionWard: 'Ward 08 - Ameerpet',
        },
      ],
    },
    {
      clauseNumber: 'Rule 6(1)(b)',
      description: 'Generic or common name of commodity not conspicuously stated',
      potentialViolationRate: 8.3,
      sampleSize: 72,
      category: 'Household Goods',
      records: [
        {
          id: 'REC-2026-008',
          timestamp: '2026-09-04 12:40 IST',
          category: 'Household Goods',
          clause: 'Rule 6(1)(b)',
          verdict: 'REVIEW',
          storeName: 'Anand Home Needs',
          jurisdictionWard: 'Ward 05 - Kukatpally',
        },
      ],
    },
  ],
  timeline: [
    { date: '2026-09-01', category: 'All Categories', passCount: 42, reviewCount: 8, potentialViolationCount: 14 },
    { date: '2026-09-02', category: 'All Categories', passCount: 50, reviewCount: 6, potentialViolationCount: 16 },
    { date: '2026-09-03', category: 'All Categories', passCount: 45, reviewCount: 11, potentialViolationCount: 10 },
    { date: '2026-09-04', category: 'All Categories', passCount: 62, reviewCount: 5, potentialViolationCount: 21 },
    { date: '2026-09-05', category: 'All Categories', passCount: 68, reviewCount: 9, potentialViolationCount: 19 },
    { date: '2026-09-06', category: 'All Categories', passCount: 61, reviewCount: 8, potentialViolationCount: 25 },
    { date: '2026-09-07', category: 'All Categories', passCount: 78, reviewCount: 14, potentialViolationCount: 32 },
  ],
};
