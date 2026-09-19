/**
 * The vendor's access token, held apart from the officer's. A vendor token carries
 * `kind: vendor` and no tier; the server refuses it on every officer route with a 401
 * and refuses an officer token on every vendor route the same way. Keeping the two in
 * different keys means neither client can ever send the other's token by accident.
 *
 * `sessionStorage`, as for officers: a session that ends with the tab.
 */

const TOKEN_KEY = 'pccs.vendor_token'

export const VENDOR_LOGIN_PATH = '/vendor/login'
export const VENDOR_HOME_PATH = '/vendor'

export function getVendorToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setVendorToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearVendorToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}
