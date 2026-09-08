import { Route, Routes } from 'react-router-dom'
import { ConsumerCapture } from './ConsumerCapture'
import { ConsumerResult } from './ConsumerResult'

/**
 * The public route tree. Mounted at /consumer/* in App.tsx with no <RequireAuth>:
 * nothing here holds a token, stores an identity, or shows one.
 */
export function ConsumerRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ConsumerCapture />} />
      <Route path="scans/:scanId" element={<ConsumerResult />} />
    </Routes>
  )
}
