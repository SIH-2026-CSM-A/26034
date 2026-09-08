import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { LOGIN_PATH, getToken } from '../services/auth'

/**
 * Gate for a whole route tree. Presence of a token only — whether it is still
 * valid is the backend's answer, and the 401 middleware in `apiClient` acts on
 * it. This never widens what a token may see.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  if (!getToken()) {
    return <Navigate to={LOGIN_PATH} replace />
  }
  return <>{children}</>
}
