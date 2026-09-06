import { Navigate, Route, Routes } from 'react-router-dom'
import { ReviewQueue } from './ReviewQueue'
import { VerdictDetail } from './VerdictDetail'

/**
 * Independent route tree for the officer surface. Mounted at /officer/* in
 * App.tsx. Never imports from AdminRoutes.
 *
 * These screens do not mount AppShell. The masthead they carry — inspection id,
 * rule-set version, capture timestamp and the offline marker — is verdict
 * furniture rather than generic chrome, and AppShell is shared with the admin
 * surface. Restyling shared chrome to serve one surface would change another
 * owner's screens, which is what keeping the two trees structurally
 * independent exists to prevent. See DESIGN.md.
 */
export function OfficerRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="queue" replace />} />
      <Route path="queue" element={<ReviewQueue />} />
      {/*
       * One fixture record is wired up, so every subject_ref resolves to it.
       * The parameter is real and is read by the route at PIP-002; nothing
       * downstream of here has to change when it starts fetching.
       */}
      <Route path="verdicts/:subjectRef" element={<VerdictDetail />} />
    </Routes>
  )
}
