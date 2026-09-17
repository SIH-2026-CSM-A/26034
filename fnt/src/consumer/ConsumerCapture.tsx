import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { ConsumerHeader } from './ConsumerHeader'
import { decodeFromImageSource, type BarcodeResult } from '../services/barcode'
import { rise, spring, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'

type Body = components['schemas']['Body_submit_consumer_image_scan_consumer_scans_image_post']

/** What the result page actually shows. Each line names a section that exists on it. */
const WHAT_YOU_GET = [
  'Each declaration the Rules ask for, with the rule that applies and whether it was found',
  'The ingredient list exactly as printed, and what each additive code is',
  'The barcode, read in your browser and never looked up',
] as const

/**
 * Photograph or choose a label. The file input with capture="environment" opens the
 * phone's own camera app, which is the most reliable camera on a mobile browser and
 * needs no permission prompt of ours; on a laptop it is a file picker.
 */
export function ConsumerCapture() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Read in the browser from the chosen photograph. Not sent, not looked up anywhere.
  const [barcode, setBarcode] = useState<BarcodeResult | null | 'pending'>(null)

  const choose = useCallback(
    (chosen: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      setFile(chosen)
      setPreviewUrl(chosen ? URL.createObjectURL(chosen) : null)
      setError(null)
      setBarcode(chosen ? 'pending' : null)
      if (chosen) {
        const img = new Image()
        img.onload = () => {
          void decodeFromImageSource(img, img.naturalWidth, img.naturalHeight).then(setBarcode)
          URL.revokeObjectURL(img.src)
        }
        img.onerror = () => setBarcode(null)
        img.src = URL.createObjectURL(chosen)
      }
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
      const { data, error: apiError } = await apiClient.POST('/consumer/scans/image', {
        body: formData as unknown as Body,
      })
      if (apiError || !data) {
        setError('The photograph could not be submitted. Check the connection and try again.')
        return
      }
      navigate(`/consumer/scans/${data.id}`, {
        state: { barcode: barcode === 'pending' ? null : barcode },
      })
    } catch {
      setError('The photograph could not be submitted. Check the connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }, [file, navigate, barcode])

  return (
    <div className="aurora">
      <ConsumerHeader />
      <main className="mx-auto grid max-w-[1120px] gap-x-16 gap-y-8 px-4 pb-16 pt-8 sm:pt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,440px)] lg:items-start">
        <motion.div variants={stagger} initial="hidden" animate="shown">
          <motion.h1 variants={rise} className="text-hero">
            Check a package label
          </motion.h1>
          <motion.p variants={rise} className="mt-4 max-w-[52ch] text-body text-mute">
            Photograph the back or front panel of any packaged product — food or not. You get
            back what the Legal Metrology (Packaged Commodities) Rules, 2011 ask for on a label,
            and whether each item could be found on yours. No sign-in, and nothing about you is
            stored.
          </motion.p>
          <motion.ul variants={rise} className="mt-8 hidden space-y-4 lg:block">
            {WHAT_YOU_GET.map((line) => (
              <li key={line} className="flex items-start gap-3 text-secondary text-ink">
                <svg viewBox="0 0 16 16" aria-hidden="true" className="mt-1 h-4 w-4 shrink-0 text-accent" fill="none">
                  <path d="M3 8.5 6.5 12 13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {line}
              </li>
            ))}
          </motion.ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring.glide, delay: 0.08 }}
          className="card p-3 shadow-e2 sm:p-4"
        >
          <label
            htmlFor="consumer-photo"
            className="group relative flex min-h-[260px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-[14px] border-2 border-dashed border-hairline bg-sunken/60 text-center transition-colors duration-base ease-out hover:border-accent/60 has-[:focus-visible]:border-accent"
          >
            <AnimatePresence mode="wait" initial={false}>
              {previewUrl ? (
                <motion.img
                  key={previewUrl}
                  src={previewUrl}
                  alt="The label you chose"
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
                  <span className="mt-4 text-body font-medium text-ink">Label photograph</span>
                  <span className="mt-1 text-secondary text-mute">
                    Fill the frame with the printed panel, in good light, without glare.
                  </span>
                </motion.span>
              )}
            </AnimatePresence>
            <input
              id="consumer-photo"
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => choose(e.target.files?.[0] ?? null)}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
          </label>

          {file && (
            <p className="mt-3 flex flex-wrap items-center gap-x-2 rounded-ctl bg-sunken/60 px-3 py-2 font-mono text-label">
              <span className="text-mute">Barcode</span>
              <span className="min-w-0 break-all text-ink">
                {barcode === 'pending'
                  ? 'reading…'
                  : barcode
                    ? `${barcode.value} · ${barcode.symbology}${barcode.checkDigitVerifies ? '' : ' · check digit does not verify'}`
                    : 'none read in this photograph'}
              </span>
            </p>
          )}

          {error && (
            <div className="mt-3">
              <Notice title="Not submitted" role="alert">
                {error}
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
            {submitting ? 'Sending…' : file ? 'Check this label' : 'Choose a photograph first'}
          </button>
          {file && !submitting && (
            <p className="mt-2 text-center text-label text-mute">Tap the photograph to choose a different one.</p>
          )}

          <p className="mt-4 px-1 text-label text-mute">
            Reading a label takes the server up to a minute. The result page keeps checking
            for you; you can leave it open.
          </p>
        </motion.div>
      </main>
    </div>
  )
}
