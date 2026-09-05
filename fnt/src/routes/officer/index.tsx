import type { RouteObject } from 'react-router-dom';
import { OfficerLayout } from '../../layouts/OfficerLayout';

/**
 * Structurally independent route tree for the Legal Metrology Officer surface.
 *
 * Module Ownership: Vineeth
 * Scope: Packaging inspection, image ingestion, PDP measurement review,
 * declaration verification, and BSA §63(4) evidence export.
 *
 * NOTE: Application screens are not implemented in FNT-001 scaffold.
 * Vineeth will mount feature screens into this independent tree.
 */
export const officerRoutes: RouteObject = {
  path: 'officer',
  element: <OfficerLayout />,
  children: [
    // Sub-routes for /officer/* will be registered here by Vineeth.
  ],
};
