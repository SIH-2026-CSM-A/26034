import { motion } from 'framer-motion'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { setToken } from '../services/auth'
import { serverMessage } from '../services/errors'
import { Logo } from '../ui/Logo'
import { rise, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'

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
    <div className="aurora flex flex-col">
      <main className="mx-auto flex w-full max-w-[440px] flex-1 flex-col justify-center px-4 py-10">
        <motion.div variants={stagger} initial="hidden" animate="shown">
          <motion.div variants={rise} className="flex items-center gap-3">
            <Logo className="h-10 w-10" />
            <div>
              <p className="font-display text-body font-semibold leading-tight tracking-tight">Maapdand</p>
              <p className="text-label text-mute">Packaged Commodity Compliance System</p>
            </div>
          </motion.div>

          <motion.div variants={rise} className="card mt-6 p-5 shadow-e2 sm:p-7">
            <h1 className="text-title">Sign in</h1>
            <p className="mt-1 text-secondary text-mute">
              Legal Metrology officer credentials. Your jurisdiction and role come from the
              token the server issues, not from anything entered here.
            </p>

            {error && (
              <div className="mt-5">
                <Notice title="Sign-in refused" role="alert">
                  <span className="font-mono">{error}</span>
                </Notice>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div>
                <label htmlFor="username" className="block text-secondary font-medium">
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
                  className="input mt-1.5 font-mono"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-secondary font-medium">
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
                  className="input mt-1.5 font-mono"
                />
              </div>

              <button type="submit" disabled={submitting} className="btn btn-primary w-full text-body">
                {submitting && (
                  <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-paper/40 border-t-paper" />
                )}
                {submitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          </motion.div>

          <motion.p variants={rise} className="mt-6 text-center text-secondary text-mute">
            Not an officer?{' '}
            <Link to="/consumer" className="font-medium text-accent underline-offset-4 hover:underline">
              Check a package label without signing in
            </Link>
          </motion.p>
          <motion.p variants={rise} className="mt-2 text-center text-secondary text-mute">
            Registered vendor?{' '}
            <Link to="/vendor/login" className="font-medium text-accent underline-offset-4 hover:underline">
              Sign in to the vendor self-check
            </Link>
          </motion.p>
        </motion.div>
      </main>
    </div>
  )
}
