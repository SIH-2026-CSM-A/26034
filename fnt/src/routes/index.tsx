import { createBrowserRouter, Navigate } from 'react-router-dom';
import { officerRoutes } from './officer';
import { adminRoutes } from './admin';

/**
 * Root Router configuration.
 *
 * Enforces structural independence between /officer/* and /admin/* trees.
 * Does NOT use single-tree conditional role rendering.
 */
export const router = createBrowserRouter([
  officerRoutes,
  adminRoutes,
  {
    path: '/',
    element: <Navigate to="/officer" replace />,
  },
  {
    path: '*',
    element: <Navigate to="/officer" replace />,
  },
]);
