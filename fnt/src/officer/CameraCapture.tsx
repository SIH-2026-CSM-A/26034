import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { serverMessage, thrownMessage } from '../services/errors'
import { awaitScanOutcome } from '../services/scans'
import { decodeFromImageSource, type BarcodeResult } from '../services/barcode'
import type { components } from '../services/generated/schema'
import { Notice } from '../ui/Notice'
import { rise, spring, stagger } from '../ui/motion'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictBanner } from './components/VerdictBanner'
import { WardSelect } from './WardSelect'
import { REFERENCE_OBJECTS, type ReferenceType } from './referenceObjects'

type CalibrationMethod = components['schemas']['CalibrationMethod']
type ProductCategory = components['schemas']['ProductCategory']
type PackageShape = components['schemas']['PackageShape']
type ScanDetail = components['schemas']['ScanDetail']
type BodySubmitImage = components['schemas']['Body_submit_image_scan_scans_image_post']

const PRODUCT_CATEGORIES: ReadonlyArray<{ value: ProductCategory; label: string }> = [
  { value: 'food', label: 'Food' },
  { value: 'cosmetics', label: 'Cosmetics' },
  { value: 'medical_device', label: 'Medical Device' },
]

const PACKAGE_SHAPES: ReadonlyArray<{ value: PackageShape; label: string }> = [
  { value: 'rectangular', label: 'Rectangular — height by width' },
  { value: 'cylindrical', label: 'Cylindrical — the label wraps the circumference' },
  { value: 'other', label: 'Other shape' },
]

// Entrances only. A panel that waited for the previous one to leave would hold a
// verdict back by the length of an exit, so nothing at this level animates out.
const enter = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: spring.glide,
}

export function CameraCapture() {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const [step, setStep] = useState<'capture' | 'preview' | 'result'>('capture')
  const [cameraActive, setCameraActive] = useState<boolean>(false)
  const [cameraError, setCameraError] = useState<string | null>(null)

  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null)
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null)
  // Decoded in the browser from the captured frame. Never sent anywhere, never looked up.
  const [barcode, setBarcode] = useState<BarcodeResult | null | 'pending'>(null)

  // Calibration & capture metadata
  const [calibrationMethod, setCalibrationMethod] = useState<CalibrationMethod>('none')
  const [referenceType, setReferenceType] = useState<ReferenceType>('coin_10')
  const [productCategory, setProductCategory] = useState<ProductCategory | ''>('')
  const [ward, setWard] = useState<string>('')
  const [institutionalConfirmed, setInstitutionalConfirmed] = useState<boolean>(false)
  // Package confirmations — what an officer confirms that no photograph establishes.
  // The same three /scans/image fields the upload form sends, so a camera capture and an
  // upload of one package cannot be evaluated under different limbs.
  const [packageShape, setPackageShape] = useState<PackageShape>('rectangular')
  const [otherLawDeclarations, setOtherLawDeclarations] = useState<boolean>(false)
  const [rule33Relaxation, setRule33Relaxation] = useState<boolean>(false)

  // API submission state
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const [waitedSeconds, setWaitedSeconds] = useState<number>(0)
  const [scanResult, setScanResult] = useState<ScanDetail | null>(null)

  // Scoped SVG pattern ID per DESIGN.md and responsive duplicate protection
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
    setBarcode('pending')
    void decodeFromImageSource(canvas, canvas.width, canvas.height).then(setBarcode)
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
      if (ward) {
        formData.append('ward', ward)
      }
      formData.append(
        'institutional_or_industrial_confirmed',
        String(institutionalConfirmed),
      )
      formData.append('package_shape', packageShape)
      formData.append('declarations_required_under_other_law', String(otherLawDeclarations))
      formData.append('rule_33_relaxation_granted', String(rule33Relaxation))

      const { data, error: apiError, response } = await apiClient.POST('/scans/image', {
        body: formData as unknown as BodySubmitImage,
      })

      if (apiError || !data) {
        setSubmissionError(serverMessage(apiError, response))
        return
      }
      // The submission is accepted before evaluation runs. Read it back until the
      // server has decided; each read is a short request that a phone network keeps.
      setWaitedSeconds(0)
      setScanResult(await awaitScanOutcome(data.id, setWaitedSeconds))
      setStep('result')
    } catch (err) {
      setSubmissionError(thrownMessage(err))
    } finally {
      setSubmitting(false)
    }
  }, [
    capturedBlob,
    calibrationMethod,
    referenceType,
    productCategory,
    ward,
    institutionalConfirmed,
    packageShape,
    otherLawDeclarations,
    rule33Relaxation,
  ])

  const resetAll = useCallback(() => {
    if (capturedUrl) {
      URL.revokeObjectURL(capturedUrl)
    }
    setCapturedBlob(null)
    setCapturedUrl(null)
    setScanResult(null)
    setSubmissionError(null)
    setCameraError(null)
    // A determination about one package, never carried to the next.
    setInstitutionalConfirmed(false)
    setPackageShape('rectangular')
    setOtherLawDeclarations(false)
    setRule33Relaxation(false)
    setStep('capture')
  }, [capturedUrl])

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="Camera" />

      <main className="mx-auto max-w-[960px] px-4 pb-28 pt-6 md:pb-16">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="max-w-[600px]">
            <h1 className="text-title">Package camera capture</h1>
            <p className="mt-1 text-secondary text-mute">
              Capture a clear, well-lit photograph of the package principal display panel (PDP) for
              legal metrology compliance review.
            </p>
          </div>
          <Link to="/officer/new" className="btn btn-quiet">
            Upload file
          </Link>
        </div>

        {/* STEPS 1 AND 2 share one frame: the still replaces the video in place. */}
        {step !== 'result' && (
          <div className="md:grid md:grid-cols-[minmax(0,400px)_minmax(0,1fr)] md:items-start md:gap-8">
            <motion.div
              {...enter}
              className="relative aspect-[3/4] max-h-[calc(100svh-18rem)] min-h-[340px] w-full overflow-hidden rounded-sheet bg-ink shadow-e2 md:sticky md:top-20 md:max-h-none"
            >
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
                  <pattern
                    id={referenceGridId}
                    width="8"
                    height="8"
                    patternUnits="userSpaceOnUse"
                  >
                    <rect
                      width="8"
                      height="8"
                      fill="none"
                      strokeWidth="0.75"
                      className="stroke-paper/70"
                    />
                  </pattern>
                </defs>

                {/* Each bracket is drawn twice, ink under paper, so it holds on a
                    bright label and a dark one, in either theme. */}
                {(['stroke-ink/40', 'stroke-paper'] as const).map((tone, layer) => (
                  <g
                    key={tone}
                    className={tone}
                    strokeWidth={layer === 0 ? 7 : 3.5}
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {/* Top-left */}
                    <path d="M 28 64 L 28 44 Q 28 28 44 28 L 64 28" />
                    {/* Top-right */}
                    <path d="M 296 28 L 316 28 Q 332 28 332 44 L 332 64" />
                    {/* Bottom-left */}
                    <path d="M 28 416 L 28 436 Q 28 452 44 452 L 64 452" />
                    {/* Bottom-right */}
                    <path d="M 296 452 L 316 452 Q 332 452 332 436 L 332 416" />
                    {/* Centre crosshair mark */}
                    <path d="M 170 240 L 190 240 M 180 230 L 180 250" strokeWidth={layer === 0 ? 4 : 1.5} />
                  </g>
                ))}

                {/* Reference Object Placement Guide (Bottom Right) */}
                {calibrationMethod === 'reference_object' && (
                  <g>
                    <rect x="230" y="350" width="92" height="92" rx="10" className="fill-ink/35" />
                    <rect
                      x="230"
                      y="350"
                      width="92"
                      height="92"
                      rx="10"
                      fill={`url(#${referenceGridId})`}
                      strokeWidth="2"
                      strokeDasharray="4 4"
                      className="stroke-paper"
                    />
                    <text
                      x="276"
                      y="400"
                      textAnchor="middle"
                      fontSize="10"
                      fontWeight="bold"
                      className="fill-paper font-mono"
                    >
                      COIN / CARD
                    </text>
                  </g>
                )}
              </svg>

              {/* The frozen frame. It arrives at full opacity — it is the frame the
                  video was already showing — and only the flash over it moves. */}
              <AnimatePresence>
                {step === 'preview' && capturedUrl && (
                  <motion.div
                    key="still"
                    exit={{ opacity: 0 }}
                    transition={spring.glide}
                    className="pointer-events-none absolute inset-0"
                  >
                    <img
                      src={capturedUrl}
                      alt="Captured package principal display panel"
                      className="h-full w-full object-cover"
                    />
                    <motion.div
                      aria-hidden="true"
                      initial={{ opacity: 0.8 }}
                      animate={{ opacity: 0 }}
                      transition={spring.glide}
                      className="absolute inset-0 bg-paper"
                    />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Status pill. Shape carries live against standby: a solid dot or a ring. */}
              <div className="glass absolute left-3 top-3 flex items-center gap-2 rounded-full px-3 py-1.5 text-ink">
                {step === 'preview' ? (
                  <span className="font-mono text-label">Captured frame</span>
                ) : (
                  <>
                    <span
                      className={`h-2.5 w-2.5 rounded-full border-2 border-ink ${
                        cameraActive ? 'animate-pulse bg-ink' : ''
                      }`}
                      aria-hidden="true"
                    />
                    <span className="font-mono text-label">
                      {cameraActive ? 'Live preview' : 'Camera standby'}
                    </span>
                  </>
                )}
              </div>

              <AnimatePresence>
                {step === 'capture' && cameraError && (
                  <motion.div
                    key="camera-error"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={spring.glide}
                    className="absolute inset-x-3 top-14"
                  >
                    <Notice
                      role="alert"
                      title="Camera error"
                      action={
                        <div className="flex flex-wrap gap-2">
                          <button type="button" onClick={startCamera} className="btn btn-primary">
                            Retry camera
                          </button>
                          <Link to="/officer/new" className="btn btn-quiet">
                            Switch to file upload →
                          </Link>
                        </div>
                      }
                    >
                      <span className="font-mono">{cameraError}</span>
                    </Notice>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Controls live inside the frame, in thumb reach. */}
              {step === 'capture' ? (
                <motion.div
                  key="shutter"
                  {...enter}
                  className="absolute inset-x-0 bottom-0 flex flex-col items-center gap-3 p-4"
                >
                  {/* Stands down for the reference guide, which needs the same corner. */}
                  {cameraActive && !cameraError && calibrationMethod !== 'reference_object' && (
                    <span className="glass rounded-full px-3 py-1.5 text-label text-ink">
                      Fit the principal display panel inside the brackets
                    </span>
                  )}
                  <motion.button
                    type="button"
                    onClick={handleCapture}
                    disabled={!cameraActive}
                    whileTap={{ scale: 0.92 }}
                    transition={spring.snap}
                    className="glass flex h-[76px] w-[76px] items-center justify-center rounded-full border border-paper/60 shadow-e3 disabled:cursor-not-allowed disabled:opacity-45"
                    aria-label="Capture photograph"
                  >
                    <span
                      className="h-[60px] w-[60px] rounded-full border-2 border-paper bg-ink"
                      aria-hidden="true"
                    />
                  </motion.button>
                </motion.div>
              ) : (
                <motion.div
                  key="confirm"
                  {...enter}
                  className="absolute inset-x-0 bottom-0 flex items-center gap-2 p-3"
                >
                  <motion.button
                    type="button"
                    onClick={handleRetake}
                    disabled={submitting}
                    whileTap={{ scale: 0.92 }}
                    transition={spring.snap}
                    aria-label="Retake photo"
                    className="glass flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-ink disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <svg viewBox="0 0 20 20" aria-hidden="true" className="h-5 w-5" fill="none">
                      <path
                        d="M4.5 10a5.5 5.5 0 1 0 1.8-4.1M4 3.5v3h3"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </motion.button>

                  <button
                    type="button"
                    onClick={handleConfirmSubmit}
                    disabled={submitting}
                    aria-busy={submitting}
                    className="btn btn-primary min-h-[56px] min-w-0 flex-1 whitespace-normal rounded-full px-4 text-center leading-tight shadow-e3 disabled:opacity-100"
                  >
                    {submitting && (
                      <svg
                        viewBox="0 0 16 16"
                        aria-hidden="true"
                        className="h-4 w-4 shrink-0 animate-spin"
                        fill="none"
                      >
                        <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
                        <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    )}
                    <span className={submitting ? 'font-mono' : ''}>
                      {submitting
                        ? waitedSeconds > 0
                          ? `Evaluating on the server… ${waitedSeconds}s`
                          : 'Submitting scan to pipeline...'
                        : 'Confirm & Submit scan'}
                    </span>
                  </button>
                </motion.div>
              )}
            </motion.div>

            <div className="mt-5 md:mt-0">
              {/* STEP 1: capture configuration */}
              {step === 'capture' && (
                <motion.div
                  key="options"
                  variants={stagger}
                  initial="hidden"
                  animate="shown"
                  className="space-y-4"
                >
                  {/* Reference Object Calibration */}
                  <motion.div variants={rise} className="card p-4 sm:p-5">
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
                      className="input mt-2"
                    >
                      <option value="none">None (uncalibrated capture)</option>
                      <option value="reference_object">Reference object in frame (coin, card or barcode)</option>
                    </select>

                    {calibrationMethod === 'reference_object' && (
                      <div className="mt-3 border-t border-hairline pt-3">
                        <label htmlFor="reference-type" className="block text-label text-mute">
                          Reference object type
                        </label>
                        <select
                          id="reference-type"
                          value={referenceType}
                          onChange={(e) => setReferenceType(e.target.value as ReferenceType)}
                          className="input mt-1"
                        >
                          {REFERENCE_OBJECTS.map((ref) => (
                            <option key={ref.value} value={ref.value}>
                              {ref.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </motion.div>

                  {/* Product Category */}
                  <motion.div variants={rise} className="card p-4 sm:p-5">
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
                      className="input mt-2"
                    >
                      <option value="">Auto-detect / Propose category from package</option>
                      {PRODUCT_CATEGORIES.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </motion.div>

                  {/* GHMC ward — where the package was inspected */}
                  <motion.div variants={rise} className="card p-4 sm:p-5">
                    <label htmlFor="camera-ward" className="block text-body font-medium">
                      Ward / jurisdiction (optional)
                    </label>
                    <p className="mt-0.5 text-secondary text-mute">
                      The GHMC ward this package was inspected in. Recorded on the scan and shown on
                      the jurisdiction map.
                    </p>
                    <WardSelect id="camera-ward" value={ward} onChange={setWard} className="input mt-2" />
                  </motion.div>

                  {/* Statutory Carve-out Checkbox */}
                  <motion.div variants={rise} className="card p-4 sm:p-5">
                    <label className="flex min-h-target cursor-pointer items-start gap-3">
                      <input
                        type="checkbox"
                        checked={institutionalConfirmed}
                        onChange={(e) => setInstitutionalConfirmed(e.target.checked)}
                        className="mt-1 h-5 w-5 shrink-0 accent-ink"
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
                  </motion.div>

                  {/* Package confirmations, behind a disclosure: three more controls on a
                      camera screen, and the defaults hold for most packages. */}
                  <motion.div variants={rise}>
                    <details className="card group p-4 sm:p-5">
                      <summary className="flex min-h-target cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
                        <div>
                          <span className="text-body font-medium">Package confirmations</span>
                          <p className="text-secondary text-mute">
                            Shape, Rule 7(5) and Rule 33. Open to change the defaults.
                          </p>
                        </div>
                        <svg
                          viewBox="0 0 20 20"
                          aria-hidden="true"
                          className="h-5 w-5 shrink-0 text-mute transition-transform group-open:rotate-180"
                          fill="none"
                        >
                          <path
                            d="M5 8l5 5 5-5"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </summary>

                      <div className="mt-3 border-t border-hairline pt-3">
                        <label htmlFor="camera-package-shape" className="block text-body font-medium">
                          Package shape
                        </label>
                        <p className="mt-0.5 text-secondary text-mute">
                          Decides which limb of Rule 7(4) computes the principal display panel area.
                        </p>
                        <select
                          id="camera-package-shape"
                          value={packageShape}
                          onChange={(e) => setPackageShape(e.target.value as PackageShape)}
                          className="input mt-2"
                        >
                          {PACKAGE_SHAPES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>

                        <div className="mt-3 space-y-3 border-t border-hairline/70 pt-3">
                          <label className="flex min-h-target cursor-pointer items-start gap-3">
                            <input
                              id="camera-other-law-declarations"
                              type="checkbox"
                              checked={otherLawDeclarations}
                              onChange={(e) => setOtherLawDeclarations(e.target.checked)}
                              className="mt-1 h-5 w-5 shrink-0 accent-ink"
                            />
                            <div>
                              <span className="text-body font-medium">Declarations also required under another law</span>
                              <p className="text-secondary text-mute">
                                Rule 7(5): the package's declarations are also required by or under another law.
                              </p>
                            </div>
                          </label>
                          <label className="flex min-h-target cursor-pointer items-start gap-3">
                            <input
                              id="camera-rule-33-relaxation"
                              type="checkbox"
                              checked={rule33Relaxation}
                              onChange={(e) => setRule33Relaxation(e.target.checked)}
                              className="mt-1 h-5 w-5 shrink-0 accent-ink"
                            />
                            <div>
                              <span className="text-body font-medium">Rule 33 relaxation granted</span>
                              <p className="text-secondary text-mute">
                                An order under Rule 33 relaxing these Rules for this package has been recorded.
                              </p>
                            </div>
                          </label>
                        </div>
                      </div>
                    </details>
                  </motion.div>
                </motion.div>
              )}

              {/* STEP 2: PREVIEW AND RETAKE */}
              {step === 'preview' && capturedUrl && (
                <motion.div key="review" {...enter} className="space-y-4">
                  <div>
                    <h2 className="font-sans text-section">Review captured photograph</h2>
                    <p className="mt-1 text-secondary text-mute">
                      Inspect image quality before submission. Ensure declarations on the principal display panel are sharp, legible, and unglared.
                    </p>
                  </div>

                  {/* Capture Details Summary */}
                  <dl className="card divide-y divide-hairline/70 px-4 font-mono text-secondary sm:px-5">
                    <div className="flex justify-between gap-4 py-3">
                      <dt className="text-mute">Barcode:</dt>
                      <dd className="text-right text-ink [overflow-wrap:anywhere]">
                        {barcode === 'pending'
                          ? 'reading…'
                          : barcode
                            ? `${barcode.value} · ${barcode.symbology}${barcode.checkDigitVerifies ? '' : ' · check digit does not verify'}`
                            : 'none read in frame'}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4 py-3">
                      <dt className="text-mute">Calibration:</dt>
                      <dd className="text-ink">{calibrationMethod}</dd>
                    </div>
                    <div className="flex justify-between gap-4 py-3">
                      <dt className="text-mute">Category:</dt>
                      <dd className="text-ink">{productCategory ? productCategory : 'Auto-detect'}</dd>
                    </div>
                    <div className="flex justify-between gap-4 py-3">
                      <dt className="text-mute">Shape:</dt>
                      <dd className="text-ink">{packageShape}</dd>
                    </div>
                  </dl>

                  {submissionError && (
                    <Notice
                      role="alert"
                      title="Scan submission error"
                      action={
                        <button type="button" onClick={handleConfirmSubmit} className="btn btn-quiet">
                          Retry submission
                        </button>
                      }
                    >
                      <span className="font-mono">{submissionError}</span>
                    </Notice>
                  )}
                </motion.div>
              )}
            </div>
          </div>
        )}

        {/* STEP 3: SUBMISSION RESULT */}
        {step === 'result' && scanResult && (
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="shown"
            className="mx-auto max-w-[640px] space-y-6"
          >
            <motion.div
              variants={rise}
              className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5"
            >
              <div className="min-w-0">
                <span className="text-label text-mute">Inspection Reference</span>
                <p className="font-mono text-body font-semibold text-ink [overflow-wrap:anywhere]">
                  {scanResult.id}
                </p>
              </div>
              <span className="rounded-full border border-hairline bg-sunken/60 px-3 py-1 font-mono text-label text-ink">
                v{scanResult.rule_set_version}
              </span>
            </motion.div>

            {/* Verdict Banner or Status. Not a staggered child: the banner brings its
                own entrance and is never queued behind a sibling. */}
            <div>
              {scanResult.verdict ? (
                <VerdictBanner verdict={scanResult.verdict} />
              ) : scanResult.quality ? (
                <Notice title="Capture refused — no verdict">
                  <p className="text-body text-ink">{scanResult.quality.instruction}</p>
                  <p className="mt-1 font-mono text-label text-mute">
                    Reason code: {scanResult.quality.reason_code}
                  </p>
                </Notice>
              ) : (
                <Notice title={`STATUS: ${scanResult.status.toUpperCase()}`}>
                  {scanResult.status === 'failed'
                    ? 'Evaluation did not finish. No finding about the package was made.'
                    : 'No verdict was issued for this scan.'}
                </Notice>
              )}
            </div>

            {/* Category Proposal block */}
            <motion.div variants={rise} className="card p-4 sm:p-5">
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
                  <div className="mt-2 rounded-ctl border border-dashed border-mute bg-sunken/60 p-3.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-ink px-2 py-0.5 font-mono text-label font-medium text-ink">
                        PROPOSAL
                      </span>
                      <span className="text-label font-medium text-ink">
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
            </motion.div>

            {/* Navigation CTAs */}
            <motion.div variants={rise} className="flex flex-col gap-3 sm:flex-row">
              <Link to={`/officer/verdicts/${scanResult.id}`} className="btn btn-primary flex-1">
                Open Review Ledger →
              </Link>
              <button type="button" onClick={resetAll} className="btn btn-quiet flex-1">
                Capture another package
              </button>
            </motion.div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
