import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';

/**
 * Admin Layout Surface.
 * Responsibility: Controller / Deputy Controller configuration, rules corpus, audit records.
 * Module Ownership: Rohan
 */
export const AdminLayout: React.FC = () => {
  const adminNav = [
    { label: 'Rule Management', to: '/admin/rules' },
    { label: 'Audit Logs', to: '/admin/audit' },
    { label: 'Inspector Hierarchy', to: '/admin/inspectors' },
  ] as const;

  return (
    <div className="min-h-screen flex flex-col bg-gov-slate-50">
      {/* Admin Header */}
      <AppHeader
        portalName="Controller Administration"
        roleBadge="STATE CONTROLLER"
        links={adminNav}
      />

      {/* Surface Status Banner */}
      <div className="bg-gov-slate-100 border-b border-gov-slate-200 px-4 py-1.5 text-xs text-gov-slate-700 font-mono flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2 h-2 rounded-full bg-gov-navy-700" aria-hidden="true" />
          <span>ADMINISTRATION CONSOLE · GAZETTE & HIERARCHY GOVERNANCE</span>
        </div>
        <div>
          <span className="text-gov-slate-500">SURFACE: /admin (Admin Workflow Foundation)</span>
        </div>
      </div>

      {/* Main Structural Content Slot */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>

      {/* Legal Footer */}
      <footer className="bg-white border-t border-gov-slate-200 py-3 px-4 text-center text-xs text-gov-slate-500 font-mono">
        Packaged Commodity Compliance System · Controller Administration Surface
      </footer>
    </div>
  );
};
