import createClient from 'openapi-fetch'
import { LOGIN_PATH, clearToken, getToken } from './auth'
import type { paths } from './generated/schema'

export const apiClient = createClient<paths>({
  // Set VITE_API_BASE_URL for anything that is not a local backend on :8000.
  // See .env.example. The dev server runs over HTTPS, so a plain-http base
  // will be blocked as mixed content by some browsers — use https there too.
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
})

apiClient.use({
  onRequest({ request }) {
    const token = getToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
  },
  onResponse({ response, schemaPath }) {
    // A 401 from the token endpoint is a rejected sign-in, and the login
    // screen has to show it. A 401 from anywhere else means the token we
    // hold is expired or revoked, so drop it and send the officer back.
    if (response.status === 401 && schemaPath !== '/auth/token') {
      clearToken()
      if (window.location.pathname !== LOGIN_PATH) {
        window.location.assign(LOGIN_PATH)
      }
    }
    return response
  },
})
