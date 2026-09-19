import createClient from 'openapi-fetch'
import type { paths } from './generated/schema'
import { VENDOR_LOGIN_PATH, clearVendorToken, getVendorToken } from './vendorAuth'

/**
 * The vendor surface's client. Same base URL and same generated `paths` as the officer
 * client, a different token and a different place to land on a 401. Only
 * `/vendors/auth/token`, `/vendor/scans` and `/vendor/scans/{id}` are ever called on it;
 * the officer routes would answer 401 to this token and the UI never offers them.
 */
export const vendorClient = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
})

vendorClient.use({
  onRequest({ request }) {
    const token = getVendorToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
  },
  onResponse({ response, schemaPath }) {
    if (response.status === 401 && schemaPath !== '/vendors/auth/token') {
      clearVendorToken()
      if (window.location.pathname !== VENDOR_LOGIN_PATH) {
        window.location.assign(VENDOR_LOGIN_PATH)
      }
    }
    return response
  },
})
