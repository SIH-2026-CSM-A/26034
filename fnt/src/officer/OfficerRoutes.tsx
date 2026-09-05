import { Route, Routes } from 'react-router-dom'
import { AppShell } from '../layout/AppShell'

function OfficerHome() {
  return <p>Officer surface — scaffold only, no screens yet.</p>
}

/**
 * Independent route tree for the officer surface (queue, dashboard, scan
 * search, batch listing validation — see SIH26034_FS.md F31-F38). Mounted at
 * /officer/* in main.tsx. Never imports from AdminRoutes.
 */
export function OfficerRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <AppShell surfaceLabel="Officer">
            <OfficerHome />
          </AppShell>
        }
      />
    </Routes>
  )
}
