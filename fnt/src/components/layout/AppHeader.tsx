import React from 'react';
import { Link } from 'react-router-dom';

export interface NavLinkItem {
  readonly label: string;
  readonly to: string;
  readonly badge?: string;
}

export interface AppHeaderProps {
  readonly portalName: string;
  readonly roleBadge: string;
  readonly links: readonly NavLinkItem[];
  readonly currentPath?: string;
}

/**
 * Shared layout header primitive for PCCS.
 * Strictly adheres to government enforcement / Legal Metrology aesthetics:
 * - Sober Deep Navy (#0B2545) primary bar
 * - Clear role badge (e.g. "LEGAL METROLOGY INSPECTOR" or "STATE CONTROLLER")
 * - High-contrast text and instant keyboard focus targets
 */
export const AppHeader: React.FC<AppHeaderProps> = ({
  portalName,
  roleBadge,
  links,
}) => {
  return (
    <header className="bg-gov-navy-900 text-white border-b-2 border-gov-navy-950 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Brand & Portal Authority Indicator */}
          <div className="flex items-center space-x-3">
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-wider uppercase text-white">
                PCCS
              </span>
              <span className="text-[10px] text-gov-slate-300 font-mono tracking-tight">
                Packaged Commodity Compliance System
              </span>
            </div>
            <div className="h-6 w-px bg-gov-navy-700" aria-hidden="true" />
            <div className="flex items-center space-x-2">
              <span className="text-xs font-semibold text-gov-slate-200">
                {portalName}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-gov-navy-800 text-gov-slate-200 border border-gov-navy-700">
                {roleBadge}
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1" aria-label="Portal Navigation">
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="px-3 py-1.5 rounded-sm text-xs font-medium text-gov-slate-200 hover:text-white hover:bg-gov-navy-800 focus-visible:outline-2 focus-visible:outline-white transition-colors"
              >
                {link.label}
                {link.badge && (
                  <span className="ml-1.5 px-1.5 py-0.2 bg-gov-navy-700 text-[10px] rounded font-mono">
                    {link.badge}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
};
