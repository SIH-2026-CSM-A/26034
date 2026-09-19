import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Login } from './auth/Login'
import { RequireAuth } from './auth/RequireAuth'

// Each surface is its own chunk, fetched when its route is first entered. The officer
// tree carries the dashboard's map and charts and the camera; a consumer or a vendor
// never downloads them.
const OfficerRoutes = lazy(() => import('./officer/OfficerRoutes').then((m) => ({ default: m.OfficerRoutes })))
const AdminRoutes = lazy(() => import('./admin/AdminRoutes').then((m) => ({ default: m.AdminRoutes })))
const ConsumerRoutes = lazy(() => import('./consumer/ConsumerRoutes').then((m) => ({ default: m.ConsumerRoutes })))
const VendorRoutes = lazy(() => import('./vendor/VendorRoutes').then((m) => ({ default: m.VendorRoutes })))

/**
 * Top-level split only — /officer/*, /admin/*, /consumer/* and /vendor/* are separate
 * route trees mounted side by side, not one tree with conditional rendering. Each
 * surface owns its own <Routes>; this file must not branch on role, user, or feature
 * flags to decide which tree renders.
 *
 * <RequireAuth> is not such a branch: it decides whether any surface renders at all,
 * and it asks only whether an officer token is held. The vendor tree carries its own
 * gate on its own token, so an officer token never opens it and a vendor token never
 * opens the officer tree. Which tree, and what that token may see inside it, is decided
 * elsewhere.
 */
export function App() {
  return (
    <Suspense fallback={<div className="aurora min-h-screen" aria-busy="true" />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/officer/*"
          element={
            <RequireAuth>
              <OfficerRoutes />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/*"
          element={
            <RequireAuth>
              <AdminRoutes />
            </RequireAuth>
          }
        />
        {/* Public. Holds no token and asks for none; the routes it calls are unauthenticated. */}
        <Route path="/consumer/*" element={<ConsumerRoutes />} />
        {/* A vendor's own token, held apart from an officer's; gated inside the tree. */}
        <Route path="/vendor/*" element={<VendorRoutes />} />
        <Route path="/" element={<Navigate to="/officer" replace />} />
      </Routes>
    </Suspense>
  )
}
