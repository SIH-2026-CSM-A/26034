import { Navigate, Route, Routes } from 'react-router-dom'
import { AdminRoutes } from './admin/AdminRoutes'
import { OfficerRoutes } from './officer/OfficerRoutes'

/**
 * Top-level split only — /officer/* and /admin/* are separate route trees
 * mounted side by side, not one tree with conditional rendering. Each
 * surface owns its own <Routes>; this file must not branch on role, user,
 * or feature flags to decide which tree renders.
 */
export function App() {
  return (
    <Routes>
      <Route path="/officer/*" element={<OfficerRoutes />} />
      <Route path="/admin/*" element={<AdminRoutes />} />
      <Route path="/" element={<Navigate to="/officer" replace />} />
    </Routes>
  )
}
