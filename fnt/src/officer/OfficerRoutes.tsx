import { Navigate, Route, Routes } from 'react-router-dom'
import { CameraCapture } from './CameraCapture'
import { ComplaintTracking } from './ComplaintTracking'
import { ReviewQueue } from './ReviewQueue'
import { ScanSubmission } from './ScanSubmission'
import { VendorSubmissions } from './VendorSubmissions'
import { VerdictDetail } from './VerdictDetail'
import OfficerDashboard from './dashboard'

/**
 * Independent route tree for the officer surface. Mounted at /officer/* in
 * App.tsx. Never imports from AdminRoutes.
 */
export function OfficerRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="queue" replace />} />
      <Route path="dashboard" element={<OfficerDashboard />} />
      <Route path="queue" element={<ReviewQueue />} />
      <Route path="vendors" element={<VendorSubmissions />} />
      <Route path="complaints" element={<ComplaintTracking />} />
      <Route path="new" element={<ScanSubmission />} />
      <Route path="submit" element={<ScanSubmission />} />
      <Route path="capture" element={<CameraCapture />} />
      <Route path="camera" element={<CameraCapture />} />
      <Route path="verdicts/:subjectRef" element={<VerdictDetail />} />
    </Routes>
  )
}
