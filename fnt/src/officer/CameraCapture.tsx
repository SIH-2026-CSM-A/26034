import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { awaitScanOutcome } from '../services/scans'
import type { components } from '../services/generated/schema'
import { VerdictBanner } from './components/VerdictBanner'
import type { Verdict as FixtureVerdict } from '../fixtures/contracts'

type CalibrationMethod = components['schemas']['CalibrationMethod']
type ProductCategory = components['schemas']['ProductCategory']
type ScanDetail = components['schemas']['ScanDetail']
type BodySubmitImage = components['schemas']['Body_submit_image_scan_scans_image_post']

const PRODUCT_CATEGORIES: ReadonlyArray<{ value: ProductCategory; label: string }> = [
  { value: 'food', label: 'Food' },
  { value: 'cosmetics', label: 'Cosmetics' },
  { value: 'medical_device', label: 'Medical Device' },
]

export function CameraCapture() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [step, setStep] = useState<'capture' | 'preview' | 'result'>('capture')
  const [cameraActive, setCameraActive] = useState<boolean>(false)
  const [cameraError, setCameraError] = useState<string | null>(null)

  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null)
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null)

  // Calibration & capture metadata
  const [calibrationMethod, setCalibrationMethod] = useState<CalibrationMethod>('none')
  const [referenceType, setReferenceType] = useState<string>('coin')
  const [productCategory, setProductCategory] = useState<ProductCategory | ''>('')
  const [institutionalConfirmed, setInstitutionalConfirmed] = useState<boolean>(false)

  // API submission state
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const [waitedSeconds, setWaitedSeconds] = useState<number>(0)
  const [scanResult, setScanResult] = useState<ScanDetail | null>(null)

  // Scoped SVG pattern ID per DESIGN.md and responsive duplicate protection
  const hatchPatternId = useId()
  const referenceGridId = useId()

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
  }, [])

  const startCamera = useCallback(async () => {
    setCameraError(null)

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        window.isSecureContext === false
          ? 'Camera access requires a secure HTTPS context or localhost.'
          : 'Camera API (getUserMedia) is not supported by this browser.',
      )
      return
    }

    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }

      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        })
      } catch {
        // Fallback for laptops/devices without discrete environment camera
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        })
      }

      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {
          // Autoplay handled by playsInline & muted
        })
      }
      setCameraActive(true)
    } catch (err) {
      setCameraActive(false)
      if (
        err instanceof DOMException &&
        (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
      ) {
        setCameraError(
          'Camera permission was denied. Please grant camera access in browser permissions.',
        )
      } else if (
        err instanceof DOMException &&
        (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError')
      ) {
        setCameraError('No camera device detected on this system.')
      } else {
        setCameraError('Unable to access camera. Please verify device camera settings.')
      }
    }
  }, [])

  // Start camera when on capture step; stop camera when moving to preview or result
  useEffect(() => {
    if (step === 'capture') {
      startCamera()
    } else {
      stopCamera()
    }

    return () => {
      stopCamera()
    }
  }, [step, startCamera, stopCamera])

  const handleCapture = useCallback(() => {
    const video = videoRef.current
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setCameraError('Camera feed not ready to capture. Please wait a moment.')
      return
    }

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      setCameraError('Failed to capture frame context.')
      return
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError('Failed to generate image file from camera capture.')
          return
        }
        const url = URL.createObjectURL(blob)
        setCapturedBlob(blob)
        setCapturedUrl(url)
        setStep('preview')
        setSubmissionError(null)
      },
      'image/jpeg',
      0.92,
    )
  }, [])

  const handleRetake = useCallback(() => {
    if (capturedUrl) {
      URL.revokeObjectURL(capturedUrl)
    }
    setCapturedBlob(null)
    setCapturedUrl(null)
    setSubmissionError(null)
    setStep('capture')
  }, [capturedUrl])

  const handleConfirmSubmit = useCallback(async () => {
    if (!capturedBlob) {
      setSubmissionError('No captured image available for submission.')
      return
    }

    setSubmitting(true)
    setSubmissionError(null)

    try {
      const formData = new FormData()
      const imageFile = new File([capturedBlob], 'pwa-camera-capture.jpg', {
        type: 'image/jpeg',
      })

      // Backend route /scans/image expects form field named 'image'
      formData.append('image', imageFile)
      formData.append('calibration_method', calibrationMethod)
      if (calibrationMethod === 'reference_object' && referenceType) {
        formData.append('reference_type', referenceType)
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
        setSubmissionError('Failed to fetch')
        return
      }
      // The submission is accepted before evaluation runs. Read it back until the
      // server has decided; each read is a short request that a phone network keeps.
      setWaitedSeconds(0)
      setScanResult(await awaitScanOutcome(data.id, setWaitedSeconds))
      setStep('result')
    } catch (err) {
      setSubmissionError(err instanceof Error ? err.message : 'Failed to fetch')
    } finally {
      setSubmitting(false)
    }
  }, [capturedBlob, calibrationMethod, referenceType, productCategory, institutionalConfirmed])

  const resetAll = useCallback(() => {
    if (capturedUrl) {
      URL.revokeObjectURL(capturedUrl)
    }
    setCapturedBlob(null)
    setCapturedUrl(null)
    setScanResult(null)
    setSubmissionError(null)
    setCameraError(null)
    setStep('capture')
  }, [capturedUrl])

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Officer Surface Masthead */}
      <header className="border-b-2 border-ink bg-paper">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-3">
          <span className="font-mono text-label font-semibold text-ink">PCCS</span>
          <span className="text-label text-mute">Camera Capture</span>
          <div className="ml-auto flex items-center gap-4">
            <Link
              to="/officer/new"
              className="flex min-h-target items-center text-label text-mute hover:text-ink"
            >
              Upload file
            </Link>
            <Link
              to="/officer/queue"
              className="flex min-h-target items-center text-label text-mute hover:text-ink"
            >
              ← Review queue
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[640px] px-4 py-6 sm:py-8">
        <div className="mb-4">
          <h1 className="text-section font-semibold sm:text-title">Package camera capture</h1>
          <p className="mt-1 text-secondary text-mute">
            Capture a clear, well-lit photograph of the package principal display panel (PDP) for
            legal metrology compliance review.
          </p>
        </div>

        {/* STEP 1: LIVE CAPTURE */}
        {step === 'capture' && (
          <div className="space-y-4">
            {cameraError && (
              <div className="border border-seal bg-paper p-4">
                <p className="text-body font-semibold text-seal">Camera error</p>
                <p className="mt-1 font-mono text-secondary text-mute">{cameraError}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={startCamera}
                    className="min-h-target border border-ink bg-paper px-4 py-2 text-label font-medium hover:bg-mute/10"
                  >
                    Retry camera
                  </button>
                  <Link
                    to="/officer/new"
                    className="flex min-h-target items-center border border-hairline px-4 py-2 text-label text-mute hover:border-ink hover:text-ink"
                  >
                    Switch to file upload →
                  </Link>
                </div>
              </div>
            )}

            {/* Video Viewfinder Container */}
            <div className="relative aspect-[3/4] w-full overflow-hidden border-2 border-ink bg-ink">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="h-full w-full object-cover"
              />

              {/* Viewfinder Overlay with Scoped SVG Pattern */}
              <svg
                viewBox="0 0 360 480"
                className="pointer-events-none absolute inset-0 h-full w-full"
                role="img"
                aria-label="Package framing guide"
              >
                <defs>
                  {/* 45-degree hatch for guide regions, scoped per DESIGN.md */}
                  <pattern
                    id={hatchPatternId}
                    width="12"
                    height="12"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M-3 3 3 -3M0 12 12 0M9 15 15 9"
                      fill="none"
                      stroke="#A8AFAC"
                      strokeWidth="2"
                    />
                  </pattern>
                  <pattern
                    id={referenceGridId}
                    width="8"
                    height="8"
                    patternUnits="userSpaceOnUse"
                  >
                    <rect width="8" height="8" fill="none" stroke="#DCDFDB" strokeWidth="0.75" />
                  </pattern>
                </defs>

                {/* Framing corner brackets for Principal Display Panel */}
                <g stroke="#DCDFDB" strokeWidth="4" fill="none" strokeLinecap="square">
                  {/* Top-left */}
                  <path d="M 28 58 L 28 28 L 58 28" />
                  {/* Top-right */}
                  <path d="M 302 28 L 332 28 L 332 58" />
                  {/* Bottom-left */}
                  <path d="M 28 422 L 28 452 L 58 452" />
                  {/* Bottom-right */}
                  <path d="M 302 452 L 332 452 L 332 422" />
                </g>

                {/* Centre crosshair mark */}
                <g stroke="#DCDFDB" strokeWidth="1.5" strokeOpacity="0.8">
                  <line x1="170" y1="240" x2="190" y2="240" />
                  <line x1="180" y1="230" x2="180" y2="250" />
                </g>

                {/* Reference Object Placement Guide (Bottom Right) */}
                {calibrationMethod === 'reference_object' && (
                  <g>
                    <rect
                      x="230"
                      y="350"
                      width="92"
                      height="92"
                      fill={`url(#${referenceGridId})`}
                      stroke="#DCDFDB"
                      strokeWidth="2"
                      strokeDasharray="4 4"
                    />
                    <text
                      x="276"
                      y="400"
                      textAnchor="middle"
                      fill="#DCDFDB"
                      fontFamily="monospace"
                      fontSize="10"
                      fontWeight="bold"
                    >
                      COIN / CARD
                    </text>
                  </g>
                )}
              </svg>

              {/* Status pill on live view */}
              <div className="absolute top-3 left-3 flex items-center gap-2 bg-ink/80 px-2.5 py-1 text-paper">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${cameraActive ? 'bg-attest' : 'bg-seal'}`}
                  aria-hidden="true"
                />
                <span className="font-mono text-label uppercase tracking-wide">
                  {cameraActive ? 'Live Preview' : 'Camera Standby'}
                </span>
              </div>
            </div>

            {/* Shutter Capture Button */}
            <div className="pt-2">
              <button
                type="button"
                onClick={handleCapture}
                disabled={!cameraActive}
                className={`flex min-h-target w-full items-center justify-center gap-3 border-2 border-ink px-6 py-4 font-mono text-body font-semibold ${
                  cameraActive
                    ? 'bg-ink text-paper hover:bg-ink/90 active:bg-ink/80'
                    : 'cursor-not-allowed border-mute bg-mute/20 text-mute'
                }`}
                aria-label="Capture photograph"
              >
                <span
                  className="inline-block h-4 w-4 rounded-full border-2 border-paper"
                  aria-hidden="true"
                />
                <span>Capture Photograph</span>
              </button>
            </div>

            {/* Capture Configuration Accordion / Options */}
            <div className="space-y-4 pt-2">
              {/* Reference Object Calibration */}
              <div className="border border-hairline bg-paper p-4">
                <label htmlFor="calibration-method" className="block text-body font-medium">
                  Calibration reference object
                </label>
                <p className="mt-0.5 text-secondary text-mute">
                  Physical reference object in frame enables millimetre scale rectification.
                </p>
                <select
                  id="calibration-method"
                  value={calibrationMethod}
                  onChange={(e) => setCalibrationMethod(e.target.value as CalibrationMethod)}
                  className="mt-2 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
                >
                  <option value="none">None (uncalibrated capture)</option>
                  <option value="reference_object">Reference coin / card in frame</option>
                </select>

                {calibrationMethod === 'reference_object' && (
                  <div className="mt-3 border-t border-hairline pt-3">
                    <label htmlFor="reference-type" className="block text-label text-mute">
                      Reference object type
                    </label>
                    <select
                      id="reference-type"
                      value={referenceType}
                      onChange={(e) => setReferenceType(e.target.value)}
                      className="mt-1 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
                    >
                      <option value="coin">Standard Indian Coin (e.g. ₹5)</option>
                      <option value="card">Standard Credit/ID Card (85.6 mm)</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Product Category */}
              <div className="border border-hairline bg-paper p-4">
                <label htmlFor="category-select" className="block text-body font-medium">
                  Product category (optional)
                </label>
                <p className="mt-0.5 text-secondary text-mute">
                  Leave unselected to allow the automated pipeline to propose category from text evidence.
                </p>
                <select
                  id="category-select"
                  value={productCategory}
                  onChange={(e) => setProductCategory(e.target.value as ProductCategory | '')}
                  className="mt-2 block min-h-target w-full border border-hairline bg-paper p-2 font-mono text-body"
                >
                  <option value="">Auto-detect / Propose category from package</option>
                  {PRODUCT_CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Statutory Carve-out Checkbox */}
              <div className="border border-hairline bg-paper p-4">
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    checked={institutionalConfirmed}
                    onChange={(e) => setInstitutionalConfirmed(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-hairline text-ink focus:ring-ink"
                  />
                  <div>
                    <span className="text-body font-medium">
                      Institutional or industrial consumer package
                    </span>
                    <p className="text-secondary text-mute">
                      Rule 3 carve-out: packaged commodity intended solely for institutional or industrial consumers.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: PREVIEW AND RETAKE */}
        {step === 'preview' && capturedUrl && (
          <div className="space-y-4">
            <div className="border border-hairline bg-paper p-3">
              <span className="font-mono text-label uppercase tracking-wider text-mute">
                Review Captured Photograph
              </span>
              <p className="mt-1 text-secondary text-ink">
                Inspect image quality before submission. Ensure declarations on the principal display panel are sharp, legible, and unglared.
              </p>
            </div>

            {/* Frozen Frame Display */}
            <div className="relative aspect-[3/4] w-full overflow-hidden border-2 border-ink bg-ink">
              <img
                src={capturedUrl}
                alt="Captured package principal display panel"
                className="h-full w-full object-cover"
              />
              <div className="absolute top-3 left-3 bg-ink px-2.5 py-1 text-paper">
                <span className="font-mono text-label uppercase">Captured Frame</span>
              </div>
            </div>

            {/* Capture Details Summary */}
            <div className="border border-hairline bg-paper p-3 font-mono text-secondary">
              <div className="flex justify-between border-b border-hairline pb-1.5">
                <span className="text-mute">Calibration:</span>
                <span className="text-ink">{calibrationMethod}</span>
              </div>
              <div className="flex justify-between pt-1.5">
                <span className="text-mute">Category:</span>
                <span className="text-ink">
                  {productCategory ? productCategory : 'Auto-detect'}
                </span>
              </div>
            </div>

            {submissionError && (
              <div className="border border-seal bg-paper p-4">
                <p className="text-body font-semibold text-seal">Scan submission error</p>
                <p className="mt-1 font-mono text-secondary text-mute">{submissionError}</p>
                <button
                  type="button"
                  onClick={handleConfirmSubmit}
                  className="mt-3 min-h-target border border-ink bg-paper px-4 py-2 text-label font-medium hover:bg-mute/10"
                >
                  Retry submission
                </button>
              </div>
            )}

            {/* Preview Action Buttons */}
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleRetake}
                disabled={submitting}
                className="flex min-h-target flex-1 items-center justify-center border border-ink bg-paper px-4 py-3 font-mono text-body text-ink hover:bg-mute/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                ← Retake photo
              </button>

              <button
                type="button"
                onClick={handleConfirmSubmit}
                disabled={submitting}
                className="flex min-h-target flex-1 items-center justify-center border border-ink bg-ink px-4 py-3 font-mono text-body text-paper hover:bg-ink/90 disabled:cursor-not-allowed disabled:bg-mute disabled:border-mute"
              >
                {submitting
                  ? waitedSeconds > 0
                    ? `Evaluating on the server… ${waitedSeconds}s`
                    : 'Submitting scan to pipeline...'
                  : 'Confirm & Submit scan'}
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: SUBMISSION RESULT */}
        {step === 'result' && scanResult && (
          <div className="space-y-6">
            <div className="border border-hairline bg-paper p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-hairline pb-4">
                <div>
                  <span className="text-label text-mute">Inspection Reference</span>
                  <p className="font-mono text-body font-semibold text-ink">{scanResult.id}</p>
                </div>
                <span className="border border-ink px-2 py-1 font-mono text-label text-ink">
                  v{scanResult.rule_set_version}
                </span>
              </div>

              {/* Verdict Banner or Status */}
              <div className="mt-6">
                {scanResult.verdict ? (
                  <VerdictBanner verdict={scanResult.verdict as FixtureVerdict} />
                ) : scanResult.quality ? (
                  <div className="border border-seal bg-paper p-4">
                    <span className="font-mono text-label uppercase text-seal">
                      Capture refused — no verdict
                    </span>
                    <p className="mt-1 text-body">{scanResult.quality.instruction}</p>
                    <p className="mt-1 font-mono text-label text-mute">
                      Reason code: {scanResult.quality.reason_code}
                    </p>
                  </div>
                ) : (
                  <div className="border border-dashed border-mute p-4">
                    <span className="font-mono text-label text-mute">
                      STATUS: {scanResult.status.toUpperCase()}
                    </span>
                    <p className="mt-1 text-secondary text-mute">
                      {scanResult.status === 'failed'
                        ? 'Evaluation did not finish. No finding about the package was made.'
                        : 'No verdict was issued for this scan.'}
                    </p>
                  </div>
                )}
              </div>

              {/* Category Proposal block */}
              <div className="mt-6 border border-hairline p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-label text-mute">Confirmed Category</span>
                  <span className="font-mono text-body font-medium text-ink">
                    {scanResult.product_category
                      ? scanResult.product_category.toUpperCase()
                      : 'None (Unconfirmed)'}
                  </span>
                </div>

                <div className="mt-3 border-t border-hairline pt-3">
                  <span className="text-label text-mute">Category Proposal</span>
                  {scanResult.category_proposal ? (
                    <div className="mt-2 border border-dashed border-query bg-paper p-3">
                      <div className="flex items-center gap-2">
                        <span className="border border-query px-1.5 py-0.5 font-mono text-label font-medium text-query">
                          PROPOSAL
                        </span>
                        <span className="text-label font-medium text-query">
                          Suggested category (pending officer confirmation)
                        </span>
                      </div>
                      <p className="mt-2 font-mono text-body font-semibold text-ink">
                        {scanResult.category_proposal.category}
                      </p>
                      <p className="mt-1 text-secondary text-mute">
                        Confidence: {(scanResult.category_proposal.confidence * 100).toFixed(0)}% •{' '}
                        {scanResult.category_proposal.reason}
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

              {/* Navigation CTAs */}
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  to={`/officer/verdicts/${scanResult.id}`}
                  className="flex min-h-target flex-1 items-center justify-center border border-ink bg-ink px-4 py-2 font-mono text-body text-paper hover:bg-ink/90"
                >
                  Open Review Ledger →
                </Link>
                <button
                  type="button"
                  onClick={resetAll}
                  className="min-h-target flex-1 border border-ink bg-paper px-4 py-2 font-mono text-body text-ink hover:bg-mute/10"
                >
                  Capture another package
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
