import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { VENDOR_LOGIN_PATH, getVendorToken } from '../services/vendorAuth'
import { VendorLogin } from './VendorLogin'
import { VendorResult } from './VendorResult'
import { VendorScan } from './VendorScan'

/** Presence of a *vendor* token only. An officer token does not open this tree. */
function RequireVendor({ children }: { children: ReactNode }) {
  if (!getVendorToken()) {
    return <Navigate to={VENDOR_LOGIN_PATH} replace />
  }
  return <>{children}</>
}

/**
 * The vendor route tree, mounted at /vendor/* in App.tsx. Its own gate and its own
 * client: nothing here imports from the officer tree, holds an officer token, or links
 * to an officer screen. Review and category confirmation are not offered because the
 * server answers a vendor token with 401 on both.
 */
export function VendorRoutes() {
  return (
    <Routes>
      <Route path="login" element={<VendorLogin />} />
      <Route
        path="/"
        element={
          <RequireVendor>
            <VendorScan />
          </RequireVendor>
        }
      />
      <Route
        path="scans/:scanId"
        element={
          <RequireVendor>
            <VendorResult />
          </RequireVendor>
        }
      />
    </Routes>
  )
}
