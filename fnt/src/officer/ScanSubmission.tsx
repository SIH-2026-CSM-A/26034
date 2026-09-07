import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { VerdictBanner } from './components/VerdictBanner'

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
  const [calibrationValue, setCalibrationValue] = useState<string>('')
  const [artworkDpi, setArtworkDpi] = useState<string>('')
  const [productCategory, setProductCategory] = useState<ProductCategory | ''>('')
  const [institutionalConfirmed, setInstitutionalConfirmed] = useState<boolean>(false)

  const [submitting, setSubmitting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScanDetail | null>(null)

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
        formData.append('file', file)
        formData.append('calibration_method', calibrationMethod)
        if (calibrationMethod === 'reference_object' && calibrationValue) {
          formData.append('calibration_value', calibrationValue)
        }
        if (calibrationMethod === 'artwork' && artworkDpi) {
          formData.append('artwork_dpi', artworkDpi)
        }
        if (productCategory) {
          formData.append('product_category', productCategory)
        }
        formData.append(
          'institutional_or_industrial_confirmed',
          String(institutionalConfirmed),
        )

        const { data, error: apiError } = await apiClient.POST('/scans/image', {
          body: formData as unknown as BodySubmitImage,
        })

        if (apiError || !data) {
          setError('Failed to fetch')
        } else {
          setResult(data)
          setError(null)
        }
      } catch {
        setError('Failed to fetch')
      } finally {
        setSubmitting(false)
      }
    },
    [file, calibrationMethod, calibrationValue, artworkDpi, productCategory, institutionalConfirmed],
  )

  const resetForm = () => {
    setFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b-2 border-ink bg-paper">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-3">
          <span className="text-label text-mute">PCCS</span>
          <span className="text-label text-mute">Scan Submission</span>
          <Link
            to="/officer/queue"
            className="ml-auto flex min-h-target items-center text-label text-mute hover:text-ink"
          >
            ← Review queue
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[800px] px-4 py-8">
        <h1 className="text-title">Submit inspection scan</h1>
        <p className="mt-1 text-secondary text-mute">
          Submit a retail package photograph or vector artwork file for automated legal metrology inspection.
        </p>

        {error && (
          <div className="mt-6 border border-seal bg-paper p-6">
            <p className="text-body font-semibold text-seal">Scan submission error</p>
            <p className="mt-1 font-mono text-secondary text-mute">{error}</p>
            <button
              type="button"
              onClick={handleSubmit}
              className="mt-4 min-h-target border border-ink px-4 py-2 text-label hover:bg-mute/10"
            >
              Retry
            </button>
          </div>
        )}

        {result ? (
          <div className="mt-6 border border-ink bg-paper p-6">
            <div className="flex items-center justify-between border-b border-hairline pb-4">
              <div>
                <span className="text-label text-mute">Inspection Reference</span>
                <p className="font-mono text-body font-semibold">{result.id}</p>
              </div>
              <span className="border border-ink px-2 py-1 font-mono text-label">
                v{result.rule_set_version}
              </span>
            </div>

            <div className="mt-6">
              {result.verdict ? (
                <VerdictBanner verdict={result.verdict} />
              ) : (
                <div className="border border-dashed border-mute p-4">
                  <span className="font-mono text-label text-mute">Status: {result.status.toUpperCase()}</span>
                  <p className="mt-1 text-secondary text-mute">No recommendation verdict issued.</p>
                </div>
              )}
            </div>

            {/* Category Proposal block (UI Rule 3) */}
            <div className="mt-6 border border-hairline p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-label text-mute">Confirmed Category</span>
                <span className="font-mono text-body font-medium">
                  {result.product_category ? result.product_category.toUpperCase() : 'None (Unconfirmed)'}
                </span>
              </div>

              <div className="mt-3 border-t border-hairline pt-3">
                <span className="text-label text-mute">Category Proposal</span>
                {result.category_proposal ? (
                  <div className="mt-2 border border-dashed border-query bg-paper p-3">
                    <div className="flex items-center gap-2">
                      <span className="border border-query px-1.5 py-0.5 font-mono text-label font-medium text-query">
                        PROPOSAL
                      </span>
                      <span className="text-label text-query font-medium">
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
                  <p className="mt-1 font-mono text-secondary text-mute">
                    None — no category proposal generated
                  </p>
                )}
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to={`/officer/verdicts/${result.id}`}
                className="flex min-h-target flex-1 items-center justify-center border border-ink bg-ink px-4 py-2 font-mono text-body text-paper hover:bg-ink/90"
              >
                Open Review Ledger →
              </Link>
              <button
                type="button"
                onClick={resetForm}
                className="min-h-target flex-1 border border-ink px-4 py-2 text-body hover:bg-mute/10"
              >
                Submit another scan
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-6">
            {/* File Upload */}
            <div className="border border-hairline bg-paper p-4">
              <label htmlFor="scan-file" className="block text-body font-medium">
                Package photograph or artwork file
              </label>
              <p className="mt-0.5 text-secondary text-mute">
                Accepts JPEG, PNG, WebP, SVG, or PDF artwork.
              </p>
              <input
                id="scan-file"
                type="file"
                accept="image/*,.svg,.pdf"
                onChange={(e) => {
                  const selected = e.target.files?.[0]
                  if (selected) setFile(selected)
                }}
                className="mt-3 block w-full border border-hairline p-2 font-mono text-secondary file:mr-4 file:min-h-target file:border file:border-ink file:bg-paper file:px-4 file:py-2 file:font-sans file:text-label hover:file:bg-mute/10"
              />
              {file && (
                <p className="mt-2 font-mono text-label text-mute">
                  Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {/* Calibration Method */}
            <div className="border border-hairline bg-paper p-4">
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
                className="mt-3 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
              >
                {CALIBRATION_METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>

              {calibrationMethod === 'reference_object' && (
                <div className="mt-3">
                  <label htmlFor="calibration-value" className="block text-label text-mute">
                    Reference object dimension (mm)
                  </label>
                  <input
                    id="calibration-value"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="e.g. 85.6"
                    value={calibrationValue}
                    onChange={(e) => setCalibrationValue(e.target.value)}
                    className="mt-1 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
                  />
                </div>
              )}

              {calibrationMethod === 'artwork' && (
                <div className="mt-3">
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
                    className="mt-1 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
                  />
                </div>
              )}
            </div>

            {/* Product Category */}
            <div className="border border-hairline bg-paper p-4">
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
                className="mt-3 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
              >
                <option value="">Auto-detect / Propose category from package</option>
                {PRODUCT_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Institutional / Industrial Carve-out */}
            <div className="border border-hairline bg-paper p-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={institutionalConfirmed}
                  onChange={(e) => setInstitutionalConfirmed(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-hairline text-ink focus:ring-ink"
                />
                <div>
                  <span className="text-body font-medium">Institutional or industrial consumer package</span>
                  <p className="text-secondary text-mute">
                    Confirm Rule 3 carve-out: packages meant for institutional or industrial consumers.
                  </p>
                </div>
              </label>
            </div>

            {/* Submit CTA */}
            <button
              type="submit"
              disabled={submitting || !file}
              className={`flex min-h-target w-full items-center justify-center border border-ink px-4 py-3 font-mono text-body ${
                submitting || !file
                  ? 'cursor-not-allowed bg-mute/20 text-mute border-mute'
                  : 'bg-ink text-paper hover:bg-ink/90'
              }`}
            >
              {submitting ? 'Submitting scan to pipeline...' : 'Submit scan for inspection'}
            </button>
          </form>
        )}
      </main>
    </div>
  )
}