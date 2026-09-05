import { Route, Routes } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'

function AdminHome() {
  return <p>Admin surface — scaffold only, no screens yet.</p>
}

/**
 * Independent route tree for the admin surface (RBAC, scheduled crawling,
 * manufacturer self-check — see SIH26034_FS.md F31-F38). Mounted at
 * /admin/* in main.tsx. Never imports from OfficerRoutes.
 */
export function AdminRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <AppShell surfaceLabel="Admin">
            <AdminHome />
          </AppShell>
        }
      />
    </Routes>
  )
}
