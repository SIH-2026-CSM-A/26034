import type { RouteObject } from 'react-router-dom';
import { AdminLayout } from '../../layouts/AdminLayout';

/**
 * Structurally independent route tree for the Controller / Administration surface.
 *
 * Module Ownership: Rohan
 * Scope: LMPC Gazette rule configuration, inspector role hierarchy,
 * audit trail inspection, and system metrics.
 *
 * NOTE: Application screens are not implemented in FNT-001 scaffold.
 * Rohan will mount feature screens into this independent tree.
 */
export const adminRoutes: RouteObject = {
  path: 'admin',
  element: <AdminLayout />,
  children: [
    // Sub-routes for /admin/* will be registered here by Rohan.
  ],
};
