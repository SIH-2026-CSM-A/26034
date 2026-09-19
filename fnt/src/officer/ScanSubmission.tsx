import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { serverMessage, thrownMessage } from '../services/errors'
import { awaitScanOutcome } from '../services/scans'
import type { components } from '../services/generated/schema'
import { spring } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictBanner } from './components/VerdictBanner'
import { WardSelect } from './WardSelect'

type CalibrationMethod = components['schemas']['CalibrationMethod']
type ProductCategory = components['schemas']['ProductCategory']
type ScanDetail = components['schemas']['ScanDetail']
type BodySubmitImage = components['schemas']['Body_submit_image_scan_scans_image_post']

const CALIBRATION_METHODS: ReadonlyArray<{ value: CalibrationMethod; label: string }> = [
  { value: 'none', label: 'None (no reference object in frame)' },
  { value: 'reference_object', label: 'Reference object (card or coin in frame)' },
  { value: 'artwork', label: 'Artwork file (vector or print artwork)' },
]

const PRODUCT_CATEGORIES: ReadonlyArray<{ value: ProductCategory; label: string }> = [
  { value: 'food', label: 'Food' },
  { value: 'cosmetics', label: 'Cosmetics' },
  { value: 'medical_device', label: 'Medical Device' },
]

export function ScanSubmission() {
  const [file, setFile] = useState<File | null>(null)
  const [calibrationMethod, setCalibrationMethod] = useState<CalibrationMethod>('none')
  const [referenceType, setReferenceType] = useState<string>('coin')
  const [artworkDpi, setArtworkDpi] = useState<string>('')
  const [productCategory, setProductCategory] = useState<ProductCategory | ''>('')
  const [ward, setWard] = useState<string>('')
  const [institutionalConfirmed, setInstitutionalConfirmed] = useState<boolean>(false)

  const [submitting, setSubmitting] = useState<boolean>(false)
  const [waitedSeconds, setWaitedSeconds] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScanDetail | null>(null)

  // Preview only. Vector and PDF artwork has no bitmap to show, so it keeps the file name alone.
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!file || !file.type.startsWith('image/')) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!file) {
        setError('Please select an image or artwork file to scan.')
        return
      }

      setSubmitting(true)
      setError(null)
      setResult(null)

      try {
        const formData = new FormData()
        // The backend reads the upload from the form field named 'image'.
        formData.append('image', file)
        formData.append('calibration_method', calibrationMethod)
        if (calibrationMethod === 'reference_object' && referenceType) {
          formData.append('reference_type', referenceType)
        }
        if (calibrationMethod === 'artwork' && artworkDpi) {
          formData.append('artwork_dpi', artworkDpi)
        }
        if (productCategory) {
          formData.append('product_category', productCategory)
        }
        if (ward) {
          formData.append('ward', ward)
        }
        formData.append(
          'institutional_or_industrial_confirmed',
          String(institutionalConfirmed),
        )

        const { data, error: apiError, response } = await apiClient.POST('/scans/image', {
          body: formData as unknown as BodySubmitImage,
        })

        if (apiError || !data) {
          setError(serverMessage(apiError, response))
          return
        }
        // The submission is accepted before evaluation runs. Read it back until the
        // server has decided; each read is a short request that a phone network keeps.
        setWaitedSeconds(0)
        setResult(await awaitScanOutcome(data.id, setWaitedSeconds))
        setError(null)
      } catch (err) {
        setError(thrownMessage(err))
      } finally {
        setSubmitting(false)
      }
    },
    [file, calibrationMethod, referenceType, artworkDpi, productCategory, ward, institutionalConfirmed],
  )

  const resetForm = () => {
    setFile(null)
    setResult(null)
    setError(null)
    // A determination about one package, never carried to the next.
    setInstitutionalConfirmed(false)
  }

  const reveal = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0 },
    transition: spring.glide,
  }

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="New scan" />

      <main className="mx-auto max-w-[720px] px-4 pb-28 pt-6 md:pb-16">
        <h1 className="text-title">Submit inspection scan</h1>
        <p className="mt-2 text-secondary text-mute">
          Submit a retail package photograph or vector artwork file for automated legal metrology inspection.
        </p>

        <AnimatePresence initial={false}>
          {error && (
            <motion.div key="error" {...reveal} className="mt-6">
              <Notice
                role="alert"
                title="Scan submission error"
                action={
                  <button type="button" onClick={handleSubmit} className="btn btn-quiet">
                    Retry
                  </button>
                }
              >
                <span className="font-mono [overflow-wrap:anywhere]">{error}</span>
              </Notice>
            </motion.div>
          )}
        </AnimatePresence>

        {result ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.glide}
            className="mt-6 space-y-6"
          >
            <div className="card flex flex-wrap items-center justify-between gap-3 p-5 sm:p-6">
              <div className="min-w-0">
                <span className="text-label text-mute">Inspection reference</span>
                <p className="font-mono text-body font-semibold [overflow-wrap:anywhere]">{result.id}</p>
              </div>
              <span className="rounded-full border border-hairline bg-sunken/60 px-3 py-1 font-mono text-label text-mute">
                v{result.rule_set_version}
              </span>
            </div>

            {result.verdict ? (
              <VerdictBanner verdict={result.verdict} />
            ) : result.quality ? (
              // A refused photograph is a statement about the photograph, so it takes the
              // hatch-and-mute treatment and nothing from the seal palette.
              <div className="rounded-card border border-dotted border-mute bg-surface bg-hatch p-2">
                <div className="rounded-[14px] bg-surface p-4 sm:p-5">
                  <span className="text-label font-medium text-mute">Capture refused — no verdict</span>
                  <p className="mt-1 text-body">{result.quality.instruction}</p>
                  <p className="mt-2 font-mono text-label text-mute">Reason code: {result.quality.reason_code}</p>
                </div>
              </div>
            ) : (
              <div className="card border-dashed p-5 shadow-none sm:p-6">
                <span className="font-mono text-label text-mute">Status: {result.status.toUpperCase()}</span>
                <p className="mt-1 text-secondary text-mute">
                  {result.status === 'failed'
                    ? 'Evaluation did not finish. No finding about the package was made.'
                    : 'No verdict was issued for this scan.'}
                </p>
              </div>
            )}

            {/* Category Proposal block (UI Rule 3) */}
            <div className="card p-5 sm:p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-label text-mute">Confirmed category</span>
                <span className="font-mono text-body font-medium">
                  {result.product_category ? result.product_category.toUpperCase() : 'None (Unconfirmed)'}
                </span>
              </div>

              <div className="mt-4 border-t border-hairline/70 pt-4">
                <span className="text-label text-mute">Category proposal</span>
                {result.category_proposal ? (
                  <div className="mt-2 rounded-ctl border border-dashed border-query bg-query-tint p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-dashed border-query bg-surface px-2.5 py-0.5 text-label font-medium text-query">
                        Proposal
                      </span>
                      <span className="text-label font-medium text-query">
                        Suggested category (pending officer confirmation)
                      </span>
                    </div>
                    <p className="mt-2 font-mono text-body font-semibold">
                      {result.category_proposal.category}
                    </p>
                    <p className="mt-1 text-secondary text-mute">
                      Confidence: {(result.category_proposal.confidence * 100).toFixed(0)}% • {result.category_proposal.reason}
                    </p>
                    <p className="mt-2 text-label text-mute">
                      A proposal is not a confirmation. Officer review is required to confirm category on the ledger.
                    </p>
                  </div>
                ) : (
                  <p className="mt-1 text-secondary text-mute">
                    None — no category proposal generated
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link to={`/officer/verdicts/${result.id}`} className="btn btn-primary flex-1">
                Open review ledger
                <span aria-hidden="true">→</span>
              </Link>
              <button type="button" onClick={resetForm} className="btn btn-quiet flex-1">
                Submit another scan
              </button>
            </div>
          </motion.div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-6">
            {/* File Upload */}
            <div className="card p-5 sm:p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <label htmlFor="scan-file" className="block text-body font-medium">
                  Package photograph or artwork file
                </label>
                <Link
                  to="/officer/capture"
                  className="text-secondary font-medium text-accent underline-offset-4 hover:underline"
                >
                  Switch to live camera →
                </Link>
              </div>
              <p className="mt-0.5 text-secondary text-mute">
                Accepts JPEG, PNG, WebP, SVG, or PDF artwork.
              </p>
              {/* The native input covers the whole zone, so tap, keyboard and drop all reach it. */}
              <div className="relative mt-4 flex min-h-[176px] flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-hairline bg-sunken/40 p-4 text-center transition-colors duration-base ease-out focus-within:border-accent hover:border-mute/60">
                <input
                  id="scan-file"
                  type="file"
                  accept="image/*,.svg,.pdf"
                  onChange={(e) => {
                    const selected = e.target.files?.[0]
                    if (selected) setFile(selected)
                  }}
                  className="absolute inset-0 h-full w-full cursor-pointer rounded-card opacity-0"
                />
                {previewUrl && (
                  <motion.img
                    key={previewUrl}
                    src={previewUrl}
                    alt="Preview of the selected photograph"
                    initial={{ opacity: 0, scale: 0.97 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={spring.glide}
                    className="max-h-64 w-auto max-w-full rounded-card border border-hairline/70 object-contain shadow-e1"
                  />
                )}
                {!file && (
                  <svg viewBox="0 0 24 24" aria-hidden="true" className="h-8 w-8 text-mute" fill="none">
                    <path
                      d="M12 16V5m0 0-4 4m4-4 4 4M4.5 15.5v3h15v-3"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                {file ? (
                  <p className="font-mono text-label text-mute [overflow-wrap:anywhere]">
                    Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </p>
                ) : (
                  <p className="text-secondary font-medium text-ink">Choose a file, or drop one here</p>
                )}
                {file && <p className="text-label text-mute">Tap to choose a different file</p>}
              </div>
            </div>

            {/* Calibration Method */}
            <div className="card relative p-5 sm:p-6">
              <label htmlFor="calibration-method" className="block text-body font-medium">
                Calibration method
              </label>
              <p className="mt-0.5 text-secondary text-mute">
                Defines the real-world scale reference for Rule 7 letter height evaluation.
              </p>
              <select
                id="calibration-method"
                value={calibrationMethod}
                onChange={(e) => setCalibrationMethod(e.target.value as CalibrationMethod)}
                className="input mt-3"
              >
                {CALIBRATION_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>

              <AnimatePresence mode="popLayout" initial={false}>
                {calibrationMethod === 'reference_object' && (
                  <motion.div key="reference" {...reveal} className="mt-4">
                    <label htmlFor="reference-type" className="block text-label text-mute">
                      Reference object type
                    </label>
                    <select
                      id="reference-type"
                      value={referenceType}
                      onChange={(e) => setReferenceType(e.target.value)}
                      className="input mt-1.5"
                    >
                      <option value="coin">Standard Indian Coin (e.g. ₹5)</option>
                      <option value="card">Standard Credit/ID Card (85.6 mm)</option>
                    </select>
                  </motion.div>
                )}

                {calibrationMethod === 'artwork' && (
                  <motion.div key="artwork" {...reveal} className="mt-4">
                    <label htmlFor="artwork-dpi" className="block text-label text-mute">
                      Artwork DPI
                    </label>
                    <input
                      id="artwork-dpi"
                      type="number"
                      step="1"
                      min="72"
                      placeholder="e.g. 300"
                      value={artworkDpi}
                      onChange={(e) => setArtworkDpi(e.target.value)}
                      className="input mt-1.5 font-mono"
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Product Category */}
            <div className="card p-5 sm:p-6">
              <label htmlFor="product-category" className="block text-body font-medium">
                Product category (optional)
              </label>
              <p className="mt-0.5 text-secondary text-mute">
                Leave unselected to allow the OCR reader to propose a category with evidence spans.
              </p>
              <select
                id="product-category"
                value={productCategory}
                onChange={(e) => setProductCategory(e.target.value as ProductCategory | '')}
                className="input mt-3"
              >
                <option value="">Auto-detect / Propose category from package</option>
                {PRODUCT_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* GHMC ward — where the package was inspected */}
            <div className="card p-5 sm:p-6">
              <label htmlFor="ghmc-ward" className="block text-body font-medium">
                Ward / jurisdiction (optional)
              </label>
              <p className="mt-0.5 text-secondary text-mute">
                The GHMC ward this package was inspected in. Recorded on the scan and shown on
                the jurisdiction map. Leave unset if not applicable.
              </p>
              <WardSelect id="ghmc-ward" value={ward} onChange={setWard} className="input mt-3" />
            </div>

            {/* Institutional / Industrial Carve-out */}
            <div className="card p-5 sm:p-6">
              <label className="flex min-h-target cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={institutionalConfirmed}
                  onChange={(e) => setInstitutionalConfirmed(e.target.checked)}
                  className="mt-1 h-5 w-5 shrink-0 accent-ink"
                />
                <div>
                  <span className="text-body font-medium">Institutional or industrial consumer package</span>
                  <p className="text-secondary text-mute">
                    Confirm Rule 3 carve-out: packages meant for institutional or industrial consumers.
                  </p>
                </div>
              </label>
            </div>

            {/* Submit CTA. Full width, so the progress text never resizes it. */}
            <button
              type="submit"
              disabled={submitting || !file}
              aria-busy={submitting}
              className="btn btn-primary w-full py-3"
            >
              {submitting && (
                <span
                  aria-hidden="true"
                  className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-paper/30 border-t-paper"
                />
              )}
              <span className="tabular">
                {submitting
                  ? waitedSeconds > 0
                    ? `Evaluating on the server… ${waitedSeconds}s`
                    : 'Submitting scan to pipeline...'
                  : 'Submit scan for inspection'}
              </span>
            </button>
          </form>
        )}
      </main>
    </div>
  )
}
