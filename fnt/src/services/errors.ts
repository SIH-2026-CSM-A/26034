/**
 * What the server said, never a sentence of ours. A refusal is a 4xx carrying `detail`
 * as a string; a malformed request is a 422 carrying `detail` as a list of validation
 * errors. Anything else falls back to the status line, which is still the server
 * speaking. A thrown error — the network, a parse — is reported in its own words.
 */
export function serverMessage(error: unknown, response: Response | undefined): string {
  const detail = (error as { detail?: unknown } | null | undefined)?.detail
  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        const e = entry as { msg?: unknown; loc?: unknown }
        const where = Array.isArray(e.loc) ? e.loc.filter((p) => typeof p === 'string' && p !== 'body').join('.') : ''
        return typeof e.msg === 'string' ? (where ? `${where}: ${e.msg}` : e.msg) : null
      })
      .filter((msg): msg is string => typeof msg === 'string')
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }
  if (response) {
    return `${response.status} ${response.statusText}`.trim()
  }
  return 'No response from the server.'
}

/** A thrown value as the message shown, with no substitute wording. */
export function thrownMessage(err: unknown): string {
  return err instanceof Error && err.message ? err.message : String(err)
}
