import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';

/**
 * Officer Layout Surface.
 * Responsibility: Field Inspector & Officer compliance workflow.
 * Module Ownership: Vineeth
 */
export const OfficerLayout: React.FC = () => {
  const officerNav = [
    { label: 'Inspections', to: '/officer/inspections' },
    { label: 'Capture & Ingest', to: '/officer/capture' },
    { label: 'Evidence Register', to: '/officer/evidence' },
  ] as const;

  return (
    <div className="min-h-screen flex flex-col bg-gov-slate-50">
      {/* Officer Header */}
      <AppHeader
        portalName="Enforcement Portal"
        roleBadge="LEGAL METROLOGY INSPECTOR"
        links={officerNav}
      />

      {/* Surface Status Banner */}
      <div className="bg-gov-slate-100 border-b border-gov-slate-200 px-4 py-1.5 text-xs text-gov-slate-700 font-mono flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-600" aria-hidden="true" />
          <span>STATUTORY FRAMEWORK: Legal Metrology (Packaged Commodities) Rules, 2011</span>
        </div>
        <div>
          <span className="text-gov-slate-500">SURFACE: /officer (Officer Workflow Foundation)</span>
        </div>
      </div>

      {/* Main Structural Content Slot */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>

      {/* Legal Footer */}
      <footer className="bg-white border-t border-gov-slate-200 py-3 px-4 text-center text-xs text-gov-slate-500 font-mono">
        Packaged Commodity Compliance System · Decision Support System · It recommends. It never decides.
      </footer>
    </div>
  );
};
