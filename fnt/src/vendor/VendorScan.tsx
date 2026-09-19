import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { serverMessage, thrownMessage } from '../services/errors'
import type { components } from '../services/generated/schema'
import { vendorClient } from '../services/vendorClient'
import { rise, spring, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { VerdictTag } from '../officer/components/VerdictBanner'
import { VendorHeader } from './VendorHeader'

type Body = components['schemas']['Body_submit_vendor_image_scan_vendor_scans_image_post']
type ScanSummary = components['schemas']['ScanSummary']

function when(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

/**
 * `POST /vendor/scans/image` and `GET /vendor/scans`: a premises checks its own stock and
 * reads back what it has submitted. Same capture pattern as the consumer screen — the
 * phone's own camera through a file input — and the same polling result page.
 */
export function VendorScan() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [scans, setScans] = useState<ScanSummary[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    vendorClient
      .GET('/vendor/scans')
      .then(({ data, error: apiError, response }) => {
        if (!active) return
        if (apiError || !data) setListError(serverMessage(apiError, response))
        else setScans(data)
      })
      .catch((err: unknown) => active && setListError(thrownMessage(err)))
    return () => {
      active = false
    }
  }, [])

  const choose = useCallback(
    (chosen: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      setFile(chosen)
      setPreviewUrl(chosen ? URL.createObjectURL(chosen) : null)
      setError(null)
    },
    [previewUrl],
  )

  const submit = useCallback(async () => {
    if (!file) return
    setSubmitting(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('image', file)
      const { data, error: apiError, response } = await vendorClient.POST('/vendor/scans/image', {
        body: formData as unknown as Body,
      })
      if (apiError || !data) {
        setError(serverMessage(apiError, response))
        return
      }
      navigate(`/vendor/scans/${data.scan.id}`)
    } catch (err) {
      setError(thrownMessage(err))
    } finally {
      setSubmitting(false)
    }
  }, [file, navigate])

  return (
    <div className="aurora">
      <VendorHeader />
      <main className="mx-auto grid max-w-[1120px] gap-x-16 gap-y-8 px-4 pb-16 pt-8 sm:pt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] lg:items-start">
        <motion.div variants={stagger} initial="hidden" animate="shown">
          <motion.h1 variants={rise} className="text-hero">
            Check your own stock
          </motion.h1>
          <motion.p variants={rise} className="mt-4 max-w-[52ch] text-body text-mute">
            Photograph the principal display panel of a package on your shelf. You get back each
            declaration the Legal Metrology (Packaged Commodities) Rules, 2011 ask for and whether
            it was found. A self-check is a recommendation to you; it is not an inspection and no
            officer has confirmed anything on it.
          </motion.p>

          <motion.section variants={rise} className="mt-10">
            <h2 className="text-section">Your submissions</h2>
            {listError ? (
              <div className="mt-3">
                <Notice title="Your submissions did not load" role="alert">
                  <span className="font-mono">{listError}</span>
                </Notice>
              </div>
            ) : scans === null ? (
              <p className="mt-3 text-secondary text-mute" aria-busy="true">
                Loading…
              </p>
            ) : scans.length === 0 ? (
              <div className="mt-3">
                <Notice title="Nothing submitted yet">
                  The first package you photograph appears here with its outcome.
                </Notice>
              </div>
            ) : (
              <motion.ul variants={stagger} className="card mt-3 divide-y divide-hairline/70 px-4 sm:px-5">
                {scans.map((scan) => (
                  <motion.li key={scan.id} variants={rise}>
                    <Link
                      to={`/vendor/scans/${scan.id}`}
                      className="flex min-h-target flex-wrap items-center justify-between gap-x-3 gap-y-1 py-3"
                    >
                      <span className="font-mono text-label text-mute">
                        {scan.id.slice(0, 8)} · {when(scan.created_at)}
                      </span>
                      {scan.verdict ? (
                        <VerdictTag verdict={scan.verdict} />
                      ) : (
                        <span className="rounded-full border border-dashed border-mute px-2 py-0.5 font-mono text-label text-mute">
                          {scan.status.toUpperCase()}
                        </span>
                      )}
                    </Link>
                  </motion.li>
                ))}
              </motion.ul>
            )}
          </motion.section>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring.glide, delay: 0.08 }}
          className="card p-3 shadow-e2 sm:p-4"
        >
          <label
            htmlFor="vendor-photo"
            className="group relative flex min-h-[260px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-[14px] border-2 border-dashed border-hairline bg-sunken/60 text-center transition-colors duration-base ease-out hover:border-accent/60 has-[:focus-visible]:border-accent"
          >
            <AnimatePresence mode="wait" initial={false}>
              {previewUrl ? (
                <motion.img
                  key={previewUrl}
                  src={previewUrl}
                  alt="The package you chose"
                  initial={{ opacity: 0, scale: 1.03 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={spring.glide}
                  className="max-h-[420px] w-full object-contain"
                />
              ) : (
                <motion.span
                  key="prompt"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center px-6 py-8"
                >
                  <span className="flex h-16 w-16 items-center justify-center rounded-full bg-surface text-ink shadow-e2 transition-transform duration-base ease-out group-hover:scale-105 group-active:scale-95">
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 8.5h3.2L9 6h6l1.8 2.5H20v10H4v-10Z" />
                      <circle cx="12" cy="13.2" r="3.2" />
                    </svg>
                  </span>
                  <span className="mt-4 text-body font-medium text-ink">Package photograph</span>
                  <span className="mt-1 text-secondary text-mute">
                    Fill the frame with the printed panel, in good light, without glare.
                  </span>
                </motion.span>
              )}
            </AnimatePresence>
            <input
              id="vendor-photo"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => choose(e.target.files?.[0] ?? null)}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
          </label>

          {error && (
            <div className="mt-3">
              <Notice title="Not submitted" role="alert">
                <span className="font-mono">{error}</span>
              </Notice>
            </div>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={!file || submitting}
            className="btn btn-primary mt-3 w-full py-4 text-body"
          >
            {submitting && (
              <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-paper/40 border-t-paper" />
            )}
            {submitting ? 'Sending…' : file ? 'Check this package' : 'Choose a photograph first'}
          </button>
          <p className="mt-4 px-1 text-label text-mute">
            Reading a label takes the server up to a minute. The result page keeps checking for
            you. No size in millimetres is reported from an uncalibrated photograph.
          </p>
        </motion.div>
      </main>
    </div>
  )
}
