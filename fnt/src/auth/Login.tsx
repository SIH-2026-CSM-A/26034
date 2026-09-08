import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { setToken } from '../services/auth'

/**
 * What the server said, never a sentence of ours. A rejected sign-in is a 401
 * carrying `detail` as a string; a malformed one is a 422 carrying `detail` as
 * a list of validation errors. Anything else falls back to the status line,
 * which is still the server speaking.
 */
function serverMessage(error: unknown, response: Response): string {
  const detail = (error as { detail?: unknown } | null | undefined)?.detail
  if (typeof detail === 'string' && detail.length > 0) {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => (entry as { msg?: unknown }).msg)
      .filter((msg): msg is string => typeof msg === 'string')
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }
  return `${response.status} ${response.statusText}`.trim()
}

export function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const { data, error: apiError, response } = await apiClient.POST('/auth/token', {
        // The route is FastAPI's OAuth2 password flow, so the body is a form,
        // not JSON.
        body: { username, password, scope: '' },
        bodySerializer: (body) => new URLSearchParams(body as Record<string, string>).toString(),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      if (data) {
        setToken(data.access_token)
        navigate('/officer/queue', { replace: true })
        return
      }
      setError(serverMessage(apiError, response))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error occurred.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b-2 border-ink bg-paper">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-3">
          <span className="text-label text-mute">PCCS</span>
          <span className="text-label text-mute">Officer Sign-in</span>
        </div>
      </header>

      <main className="mx-auto max-w-[440px] px-4 py-12">
        <h1 className="text-title">Sign in</h1>
        <p className="mt-1 text-secondary text-mute">
          Legal Metrology officer credentials. Your jurisdiction and role come from the
          token the server issues, not from anything entered here.
        </p>

        {error && (
          <div className="mt-6 border border-seal bg-paper p-4" role="alert">
            <p className="text-body font-semibold text-seal">Sign-in refused</p>
            <p className="mt-1 font-mono text-secondary text-mute">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div>
            <label htmlFor="username" className="block text-body font-medium">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-2 block min-h-target w-full border border-hairline bg-paper px-3 py-2 font-mono text-body"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-body font-medium">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-2 block min-h-target w-full border border-hairline bg-paper px-3 py-2 font-mono text-body"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="min-h-target w-full border border-ink bg-ink px-4 py-2 font-mono text-body text-paper hover:bg-ink/90 disabled:opacity-60"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="mt-8 border-t border-hairline pt-4 text-secondary text-mute">
          Not an officer?{' '}
          <Link to="/consumer" className="text-ink underline underline-offset-2">
            Check a package label without signing in
          </Link>
          .
        </p>
      </main>
    </div>
  )
}
