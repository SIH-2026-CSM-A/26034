/**
 * The officer's access token, and nothing else. No React, so `apiClient` can
 * import it without pulling the UI in behind it.
 *
 * The token lives in `sessionStorage`, not `localStorage`: PCCS is used on
 * shared inspection laptops, and a session that ends with the tab is one the
 * next officer cannot inherit. The cost is signing in again after a restart.
 */

const TOKEN_KEY = 'pccs.access_token'

/** Where an unauthenticated request or a rejected token sends the officer. */
export const LOGIN_PATH = '/login'

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}
