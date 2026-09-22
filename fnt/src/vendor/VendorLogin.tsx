import { motion } from 'framer-motion'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { serverMessage, thrownMessage } from '../services/errors'
import { VENDOR_HOME_PATH, setVendorToken } from '../services/vendorAuth'
import { vendorClient } from '../services/vendorClient'
import { Logo } from '../ui/Logo'
import { rise, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'

/** `POST /vendors/auth/token`: the credentials an officer registered the premises with. */
export function VendorLogin() {
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
      const { data, error: apiError, response } = await vendorClient.POST('/vendors/auth/token', {
        // FastAPI's OAuth2 password flow: a form body, not JSON.
        body: { username, password, scope: '' },
        bodySerializer: (body) => new URLSearchParams(body as Record<string, string>).toString(),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      if (data) {
        setVendorToken(data.access_token)
        navigate(VENDOR_HOME_PATH, { replace: true })
        return
      }
      setError(serverMessage(apiError, response))
    } catch (err) {
      setError(thrownMessage(err))
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
              <p className="font-display text-body font-semibold leading-tight tracking-tight">ClauseCam</p>
              <p className="text-label text-mute">Vendor self-check</p>
            </div>
          </motion.div>

          <motion.div variants={rise} className="card mt-6 p-5 shadow-e2 sm:p-7">
            <h1 className="text-title">Vendor sign in</h1>
            <p className="mt-1 text-secondary text-mute">
              The username and password a Legal Metrology officer registered your premises with.
              What you submit here is a self-check of your own stock; it is not an inspection.
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
                <label htmlFor="vendor-username" className="block text-secondary font-medium">
                  Username
                </label>
                <input
                  id="vendor-username"
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
                <label htmlFor="vendor-password" className="block text-secondary font-medium">
                  Password
                </label>
                <input
                  id="vendor-password"
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
            <Link to="/login" className="font-medium text-accent underline-offset-4 hover:underline">
              Officer sign-in
            </Link>
            {' · '}
            <Link to="/consumer" className="font-medium text-accent underline-offset-4 hover:underline">
              Check a label without signing in
            </Link>
          </motion.p>
        </motion.div>
      </main>
    </div>
  )
}
