import React, { useState } from 'react';
import { mockDashboardData } from '../../fixtures/dashboard';
import { CategoryFilterBar } from './CategoryFilterBar';
import { HeatmapJurisdiction } from './HeatmapJurisdiction';
import { TimelineBucketChart } from './TimelineBucketChart';
import { ClauseBreakdownView } from './ClauseBreakdownView';

export const OfficerDashboard: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<string>('All Categories');
  const [selectedWard, setSelectedWard] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-slate-100 text-slate-900 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        <header className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-4 border-b border-slate-100 pb-3">
            <div>
              <h1 className="text-lg sm:text-xl font-extrabold text-slate-950 tracking-tight">
                Legal Metrology Enforcement Dashboard
              </h1>
              <p className="text-xs sm:text-sm text-slate-600">
                SIH 2026 � Problem Statement 26034 � Rule 6 Jurisdiction Monitoring
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Officer Portal Live
              </span>
            </div>
          </div>

          <CategoryFilterBar
            categories={mockDashboardData.categories}
            activeCategory={activeCategory}
            onSelectCategory={setActiveCategory}
          />
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
          <div className="lg:col-span-7 space-y-4 sm:space-y-6">
            <HeatmapJurisdiction
              wards={mockDashboardData.wards}
              activeCategory={activeCategory}
              selectedWard={selectedWard}
              onSelectWard={(id) => setSelectedWard(id === selectedWard ? null : id)}
            />
            <TimelineBucketChart timeline={mockDashboardData.timeline} />
          </div>

          <div className="lg:col-span-5">
            <ClauseBreakdownView
              clauses={mockDashboardData.clauses}
              activeCategory={activeCategory}
            />
          </div>
        </div>
      </div>
    </main>
  );
};

export default OfficerDashboard;
