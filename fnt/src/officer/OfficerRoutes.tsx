import { Navigate, Route, Routes } from 'react-router-dom'
import { CameraCapture } from './CameraCapture'
import { ReviewQueue } from './ReviewQueue'
import { ScanSubmission } from './ScanSubmission'
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
      <Route path="new" element={<ScanSubmission />} />
      <Route path="submit" element={<ScanSubmission />} />
      <Route path="capture" element={<CameraCapture />} />
      <Route path="camera" element={<CameraCapture />} />
      <Route path="verdicts/:subjectRef" element={<VerdictDetail />} />
    </Routes>
  )
}