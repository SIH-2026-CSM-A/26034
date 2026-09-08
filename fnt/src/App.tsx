import { Navigate, Route, Routes } from 'react-router-dom'
import { AdminRoutes } from './admin/AdminRoutes'
import { Login } from './auth/Login'
import { ConsumerRoutes } from './consumer/ConsumerRoutes'
import { RequireAuth } from './auth/RequireAuth'
import { OfficerRoutes } from './officer/OfficerRoutes'

/**
 * Top-level split only — /officer/* and /admin/* are separate route trees
 * mounted side by side, not one tree with conditional rendering. Each
 * surface owns its own <Routes>; this file must not branch on role, user,
 * or feature flags to decide which tree renders.
 *
 * <RequireAuth> is not such a branch: it decides whether any surface renders
 * at all, and it asks only whether a token is held. Which tree, and what that
 * token may see inside it, is decided elsewhere.
 */
export function App() {
  return (
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
      <Route path="/" element={<Navigate to="/officer" replace />} />
    </Routes>
  )
}
