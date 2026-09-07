import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { CapturePlate } from './components/CapturePlate'
import { FieldStateChip } from './components/FieldStateChip'
import { VerdictBanner, verdictLabel } from './components/VerdictBanner'

type ScanDetail = components['schemas']['ScanDetail']
type FieldFinding = components['schemas']['FieldFinding']
type FieldState = components['schemas']['FieldState']
type Verdict = components['schemas']['Verdict']
type ReviewAction = components['schemas']['ReviewAction']
type ReviewResponse = components['schemas']['ReviewResponse']
type ProductCategory = components['schemas']['ProductCategory']

const ROW_LABELS: Partial<Record<string, string>> = {
  'NET_QUANTITY|Rule 7(2), Table-I': 'Net quantity, letter height',
  'UNIT_SALE_PRICE|Rule 6(11)': 'Unit sale price basis',
  'NAME_AND_ADDRESS|Rule 6(1)(a)': 'Manufacturer name and address',
  'NET_QUANTITY|Rule 8(1) proviso': 'Free space around the quantity declaration',
  'COUNTRY_OF_ORIGIN|Rule 6(1)(aa)': 'Country of origin',
  'RETAIL_SALE_PRICE|Rule 7(2), Table-I': 'Retail sale price, letter height',
}

const PRODUCT_CATEGORIES: ReadonlyArray<{ value: ProductCategory; label: string }> = [
  { value: 'food', label: 'Food' },
  { value: 'cosmetics', label: 'Cosmetics' },
  { value: 'medical_device', label: 'Medical Device' },
]

function rowLabel(finding: FieldFinding): string {
  const clauseRef = finding.rule_snapshot?.clause_ref ?? ''
  const key = `${finding.field}|${clauseRef}`
  return ROW_LABELS[key] ?? finding.field.replace(/_/g, ' ')
}

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso)
    return new Intl.DateTimeFormat('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'Asia/Kolkata',
    }).format(date)
  } catch {
    return iso
  }
}

function Masthead({
  inspectionId,
  ruleSetVersion,
  capturedAt,
  isOnline,
}: {
  inspectionId: string
  ruleSetVersion: string
  capturedAt: string
  isOnline: boolean
}) {
  return (
    <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 py-2 lg:flex lg:items-baseline lg:gap-6 lg:py-3">
        <div className="flex items-center justify-between gap-4 lg:contents">
          <Link
            to="/officer/queue"
            className="flex min-h-target items-center text-label text-mute hover:text-ink lg:order-1"
          >
            ← Queue
          </Link>
          <span className="flex shrink-0 items-center gap-2 border border-ink px-2 py-0.5 lg:order-3 lg:ml-auto">
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.75" />
              <path d="M3.8 12.2 12.2 3.8" stroke="currentColor" strokeWidth="1.75" />
            </svg>
            <span className="font-mono text-label">
              {isOnline ? 'Online' : 'Offline — findings held on device'}
            </span>
          </span>
        </div>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-0.5 lg:order-2 lg:mt-0 lg:gap-x-6">
          <MastheadValue label="Inspection" value={inspectionId} />
          <MastheadValue label="Rule set" value={`v${ruleSetVersion}`} />
          <MastheadValue label="Captured" value={formatTimestamp(capturedAt)} />
        </div>
      </div>
    </header>
  )
}

function MastheadValue({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-baseline gap-2">
      <span className="text-label text-mute">{label}</span>
      <span className="font-mono text-label text-ink">{value}</span>
    </span>
  )
}

function MeasuredPair({ observed, expected }: { observed: string | null; expected: string | null }) {
  if (observed === null && expected === null) {
    return <span className="text-secondary text-mute">No measurement recorded.</span>
  }
  return (
    <span className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
      <span className="text-label text-mute">Measured</span>
      <span className="font-mono text-secondary text-ink">{observed ?? '—'}</span>
      <span className="text-label text-mute">Required</span>
      <span className="font-mono text-secondary text-ink">{expected ?? '—'}</span>
    </span>
  )
}

export function VerdictDetail() {
  const { subjectRef } = useParams<{ subjectRef: string }>()
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [focusedIndex, setFocusedIndex] = useState(0)

  // Category Confirmation State (UI Rule 4)
  const [confirmedCategory, setConfirmedCategory] = useState<ProductCategory | null>(null)

  // Officer Confirmation Surface State (UI Rule 1: NO pre-selection)
  const [selectedAction, setSelectedAction] = useState<ReviewAction | null>(null)
  const [overriddenVerdict, setOverriddenVerdict] = useState<Verdict | null>(null)
  const [reviewNote, setReviewNote] = useState<string>('')
  const [submittingReview, setSubmittingReview] = useState<boolean>(false)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null)

  const fetchScan = useCallback(async () => {
    if (!subjectRef) {
      setError('No inspection reference provided.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: apiError } = await apiClient.GET('/scans/{scan_id}', {
        params: {
          path: { scan_id: subjectRef },
        },
      })

      if (apiError || !data) {
        setError('Failed to fetch')
        setScan(null)
      } else {
        setScan(data)
        setError(null)
        if (data.product_category) {
          setConfirmedCategory(data.product_category as ProductCategory)
        }
        const insufficientIdx = data.findings.findIndex(
          (f) => f.state === 'INSUFFICIENT_EVIDENCE',
        )
        setFocusedIndex(insufficientIdx === -1 ? 0 : insufficientIdx)
      }
    } catch {
      setError('Failed to fetch')
      setScan(null)
    } finally {
      setLoading(false)
    }
  }, [subjectRef])

  useEffect(() => {
    fetchScan()
  }, [fetchScan])

  const findings = scan?.findings ?? []
  const focused = findings[focusedIndex]

  // UI Rule 3: Insufficient evidence visibility
  const insufficientFindings = findings.filter(
    (f) => f.state === 'INSUFFICIENT_EVIDENCE',
  )

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!scan || !selectedAction) return

    // Validation matching backend model_validator
    if (selectedAction === 'override' && !overriddenVerdict) {
      setReviewError('An override requires stating the substituted verdict.')
      return
    }
    if (selectedAction !== 'confirm' && !reviewNote.trim()) {
      setReviewError(`Action ${selectedAction} requires a text note explaining the decision.`)
      return
    }

    setSubmittingReview(true)
    setReviewError(null)

    try {
      const { data, error: apiError } = await apiClient.POST(
        '/scans/{scan_id}/review',
        {
          params: {
            path: { scan_id: scan.id },
          },
          body: {
            action: selectedAction,
            note: reviewNote.trim() || null,
            overridden_verdict: selectedAction === 'override' ? overriddenVerdict : null,
          },
        },
      )

      if (apiError || !data) {
        setReviewError('Failed to submit review')
      } else {
        setReviewResult(data)
        setReviewError(null)
      }
    } catch {
      setReviewError('Failed to submit review')
    } finally {
      setSubmittingReview(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-paper text-ink">
        <header className="border-b-2 border-ink px-4 py-3">
          <span className="text-label text-mute">PCCS Inspection</span>
        </header>
        <main className="mx-auto max-w-[1280px] p-8 text-center">
          <p className="font-mono text-body text-mute animate-pulse">Loading inspection details from API...</p>
        </main>
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="min-h-screen bg-paper text-ink">
        <header className="border-b-2 border-ink px-4 py-3">
          <Link to="/officer/queue" className="flex min-h-target items-center text-label text-mute hover:text-ink">
            ← Back to queue
          </Link>
        </header>
        <main className="mx-auto max-w-[1280px] p-6">
          <div className="border border-seal bg-paper p-6">
            <p className="text-body font-semibold text-seal">Unable to load inspection</p>
            <p className="mt-1 font-mono text-secondary text-mute">{error ?? 'Scan not found'}</p>
            <button
              type="button"
              onClick={fetchScan}
              className="mt-4 min-h-target border border-ink px-4 py-2 text-label hover:bg-mute/10"
            >
              Retry
            </button>
          </div>
        </main>
      </div>
    )
  }

  const isOverrideInvalid =
    selectedAction === 'override' && (!overriddenVerdict || !reviewNote.trim())
  const isNonConfirmNoteMissing =
    selectedAction !== null &&
    selectedAction !== 'confirm' &&
    selectedAction !== 'override' &&
    !reviewNote.trim()
  const isSubmitDisabled =
    selectedAction === null || submittingReview || isOverrideInvalid || isNonConfirmNoteMissing

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Masthead
        inspectionId={scan.id}
        ruleSetVersion={scan.rule_set_version}
        capturedAt={scan.created_at}
        isOnline={!error}
      />

      <main className="mx-auto max-w-[1280px] px-4 pb-48 lg:pb-40">
        <h1 className="sr-only">Verdict detail for {scan.id}</h1>

        <div className="lg:grid lg:grid-cols-[1fr_400px] lg:gap-10">
          <div className="min-w-0">
            {/* Recommendation verdict banner (UI Rule 2) */}
            <div className="pt-6">
              {scan.verdict ? (
                <div>
                  <VerdictBanner verdict={scan.verdict} />
                  <p className="mt-1 text-label text-mute">
                    Recommendation only. Official determination requires officer review.
                  </p>
                </div>
              ) : (
                <div className="border border-dashed border-mute p-4">
                  <span className="font-mono text-label text-mute">Status: {scan.status.toUpperCase()}</span>
                  <p className="mt-1 text-secondary text-mute">No recommendation verdict issued.</p>
                </div>
              )}
            </div>

            {/* Category confirmation control (UI Rule 4) */}
            <section aria-label="Category classification" className="mt-6 border border-hairline bg-paper p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <span className="text-label text-mute">Confirmed Product Category</span>
                  <div className="mt-0.5 flex items-center gap-2">
                    <p className="font-mono text-body font-semibold">
                      {confirmedCategory ? confirmedCategory.toUpperCase() : 'None (Unconfirmed)'}
                    </p>
                    {confirmedCategory ? (
                      <span className="border border-attest px-1.5 py-0.2 font-mono text-label text-attest">
                        OFFICER CONFIRMED
                      </span>
                    ) : (
                      <span className="border border-dashed border-mute px-1.5 py-0.2 font-mono text-label text-mute">
                        AWAITING OFFICER CONFIRMATION
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-label text-mute">
                    Sector-specific rules remain held under INSUFFICIENT_EVIDENCE until an officer confirms the category.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <label htmlFor="select-category" className="text-label text-mute">
                    Override / Correct:
                  </label>
                  <select
                    id="select-category"
                    value={confirmedCategory ?? ''}
                    onChange={(e) => setConfirmedCategory((e.target.value as ProductCategory) || null)}
                    className="border border-hairline bg-paper px-2 py-1 font-mono text-label text-ink"
                  >
                    <option value="">Unconfirmed</option>
                    {PRODUCT_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 border-t border-hairline pt-3">
                <span className="text-label text-mute">Reader Category Proposal</span>
                {scan.category_proposal ? (
                  <div className="mt-2 border border-dashed border-query bg-paper p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="border border-query px-1.5 py-0.5 font-mono text-label font-medium text-query">
                          PROPOSAL
                        </span>
                        <span className="text-label text-query font-medium">
                          Suggested category (pending officer confirmation)
                        </span>
                      </div>
                    </div>
                    <p className="mt-2 font-mono text-body font-semibold">
                      {scan.category_proposal.category.toUpperCase()}
                    </p>
                    <p className="mt-1 text-secondary text-mute">
                      Confidence: {(scan.category_proposal.confidence * 100).toFixed(0)}% • {scan.category_proposal.reason}
                    </p>
                    {scan.category_proposal.span_refs.length > 0 && (
                      <div className="mt-2">
                        <span className="text-label text-mute">Evidence spans cited:</span>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {scan.category_proposal.span_refs.map((spanId) => (
                            <span
                              key={spanId}
                              className="border border-ink bg-paper px-2 py-0.5 font-mono text-label text-ink"
                            >
                              {spanId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="mt-3.5 flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setConfirmedCategory(scan.category_proposal?.category ?? null)}
                        className={`min-h-target border px-3 py-1.5 font-mono text-label transition-colors ${
                          confirmedCategory === scan.category_proposal.category
                            ? 'border-attest bg-attest text-paper'
                            : 'border-ink bg-paper text-ink hover:bg-mute/10'
                        }`}
                      >
                        {confirmedCategory === scan.category_proposal.category
                          ? '✓ Confirmed as proposed'
                          : `Confirm proposal: ${scan.category_proposal.category}`}
                      </button>
                      {confirmedCategory && confirmedCategory !== scan.category_proposal.category && (
                        <span className="font-mono text-label text-query">
                          (Corrected to {confirmedCategory.toUpperCase()})
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-label text-mute">
                      A proposal is never the scan's actual category until confirmed or corrected by the officer.
                    </p>
                  </div>
                ) : (
                  <p className="mt-1 font-mono text-secondary text-mute">
                    None — no category proposal recorded on this scan
                  </p>
                )}
              </div>
            </section>

            {/* Insufficient Evidence visibility banner (UI Rule 3) */}
            {insufficientFindings.length > 0 && (
              <section aria-label="Evidence status" className="mt-6 border border-dotted border-mute bg-paper p-4">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 rounded-full border-2 border-mute" />
                  <span className="font-mono text-label font-semibold text-ink">
                    INSUFFICIENT EVIDENCE DETECTED
                  </span>
                  <span className="text-label text-mute">
                    ({insufficientFindings.length} declaration{insufficientFindings.length === 1 ? '' : 's'} could not be read)
                  </span>
                </div>
                <p className="mt-2 text-secondary text-mute">
                  The automated reader could not obtain readable evidence for all required declarations. Confirming this scan acknowledges unreadable evidence, not compliance. Consider whether recapture is required.
                </p>
              </section>
            )}

            {scan.quality && (
              <div className="mt-6 border border-query bg-paper p-4">
                <span className="text-label font-medium text-query">Capture Quality Note</span>
                <p className="mt-1 text-body">{scan.quality.instruction}</p>
                <p className="mt-1 font-mono text-label text-mute">Reason code: {scan.quality.reason_code}</p>
              </div>
            )}

            {/* Capture Plate */}
            <div className="mt-6 lg:hidden">
              <CapturePlate
                pinnedSpans={[]}
                showUnresolvedRegion={focused?.state === 'INSUFFICIENT_EVIDENCE'}
                inspectionId={scan.id}
              />
            </div>

            {/* Findings ledger */}
            <h2 className="mt-8 text-section">Findings</h2>
            {findings.length === 0 ? (
              <p className="mt-4 border border-dotted border-mute p-6 text-secondary text-mute">
                No rule findings evaluated for this inspection.
              </p>
            ) : (
              <ul className="m-0 mt-3 list-none border-t border-hairline p-0">
                {findings.map((finding, index) => (
                  <LedgerRow
                    key={`${finding.field}-${finding.rule_snapshot?.rule_id ?? index}`}
                    finding={finding}
                    focused={index === focusedIndex}
                    onFocus={() => setFocusedIndex(index)}
                  />
                ))}
              </ul>
            )}
          </div>

          <aside className="hidden lg:block lg:pt-6">
            <div className="lg:sticky lg:top-24">
              <CapturePlate
                pinnedSpans={[]}
                showUnresolvedRegion={focused?.state === 'INSUFFICIENT_EVIDENCE'}
                inspectionId={scan.id}
              />
            </div>
          </aside>
        </div>
      </main>

      {/* Officer Confirmation Control Surface */}
      <footer className="fixed bottom-0 left-0 right-0 z-20 border-t-8 border-double border-ink bg-ink text-paper">
        <div className="mx-auto max-w-[1280px] px-4 py-3">
          {reviewResult ? (
            <div className="flex flex-wrap items-center justify-between gap-3 bg-paper p-3 text-ink">
              <div>
                <span className="border border-attest px-1.5 py-0.5 font-mono text-label font-semibold text-attest">
                  REVIEW RECORDED
                </span>
                <p className="mt-1 font-mono text-label">
                  Action: {reviewResult.action.toUpperCase()} • Finalised: {reviewResult.finalised ? 'Yes' : 'No'}
                </p>
                {reviewResult.overridden_verdict && (
                  <p className="font-mono text-label">
                    Substituted verdict: {reviewResult.overridden_verdict}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  setReviewResult(null)
                  setSelectedAction(null)
                  setReviewNote('')
                  setOverriddenVerdict(null)
                }}
                className="min-h-target border border-ink px-3 py-1.5 text-label hover:bg-mute/10"
              >
                Modify determination
              </button>
            </div>
          ) : (
            <form onSubmit={handleReviewSubmit} className="space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-mono text-label text-hairline">
                  Officer confirmation surface • Determination step
                </p>
                <p className="text-label text-hairline">
                  Recommendation: {scan.verdict ? verdictLabel(scan.verdict) : 'NONE'}
                </p>
              </div>

              {/* Insufficient Evidence prominent banner during confirmation (UI Rule 3) */}
              {insufficientFindings.length > 0 && (
                <div className="border border-dotted border-mute/80 bg-ink p-2.5 text-paper">
                  <div className="flex items-center gap-2">
                    <span className="inline-block h-2.5 w-2.5 rounded-full border border-paper bg-query" />
                    <span className="font-mono text-label font-semibold text-paper">
                      INSUFFICIENT EVIDENCE DETECTED ({insufficientFindings.length} DECLARATION{insufficientFindings.length === 1 ? '' : 'S'})
                    </span>
                  </div>
                  <p className="mt-1 text-label text-hairline">
                    Confirming records an acknowledgement of unreadable evidence, NOT compliance. Lack of evidence must not be folded into a pass state.
                  </p>
                </div>
              )}

              {/* Action selection buttons (UI Rule 1: NO PRE-SELECTION) */}
              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="font-mono text-label text-hairline">
                    Disposition choices (No default selected • Explicit selection required):
                  </span>
                  {selectedAction === null && (
                    <span className="font-mono text-label text-query">
                      * Please select an action
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedAction(selectedAction === 'confirm' ? null : 'confirm')}
                    className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body transition-colors ${
                      selectedAction === 'confirm'
                        ? 'border-2 border-paper bg-paper font-semibold text-ink'
                        : 'border border-hairline bg-ink font-normal text-paper hover:bg-hairline/20'
                    }`}
                  >
                    Confirm
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction(selectedAction === 'override' ? null : 'override')}
                    className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body transition-colors ${
                      selectedAction === 'override'
                        ? 'border-2 border-paper bg-paper font-semibold text-ink'
                        : 'border border-hairline bg-ink font-normal text-paper hover:bg-hairline/20'
                    }`}
                  >
                    Override
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction(selectedAction === 'reject' ? null : 'reject')}
                    className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body transition-colors ${
                      selectedAction === 'reject'
                        ? 'border-2 border-paper bg-paper font-semibold text-ink'
                        : 'border border-hairline bg-ink font-normal text-paper hover:bg-hairline/20'
                    }`}
                  >
                    Reject
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedAction(selectedAction === 'annotate' ? null : 'annotate')}
                    className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body transition-colors ${
                      selectedAction === 'annotate'
                        ? 'border-2 border-paper bg-paper font-semibold text-ink'
                        : 'border border-hairline bg-ink font-normal text-paper hover:bg-hairline/20'
                    }`}
                  >
                    Annotate
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setSelectedAction(selectedAction === 'request_recapture' ? null : 'request_recapture')
                    }
                    className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body transition-colors ${
                      selectedAction === 'request_recapture'
                        ? 'border-2 border-paper bg-paper font-semibold text-ink'
                        : 'border border-hairline bg-ink font-normal text-paper hover:bg-hairline/20'
                    }`}
                  >
                    Request recapture
                  </button>
                </div>
              </div>

              {/* Action-specific fields when an action is selected */}
              {selectedAction && (
                <div className="space-y-2.5 border-t border-hairline/40 pt-2.5">
                  {/* Notice when confirming with insufficient evidence (UI Rule 3) */}
                  {selectedAction === 'confirm' && insufficientFindings.length > 0 && (
                    <div className="border border-query bg-paper p-2.5 text-ink">
                      <p className="font-mono text-label font-bold text-query">
                        NOTICE: CONFIRMING WITH UNREADABLE EVIDENCE
                      </p>
                      <p className="mt-0.5 text-label text-ink">
                        Confirming records an explicit acknowledgement that {insufficientFindings.length} declaration{insufficientFindings.length === 1 ? '' : 's'} could not be read. This will NOT be recorded as statutory compliance.
                      </p>
                    </div>
                  )}

                  {/* Override requires selecting overridden_verdict (UI Rule 2 & UI Rule 6) */}
                  {selectedAction === 'override' && (
                    <div>
                      <label htmlFor="overridden-verdict" className="block text-label text-hairline">
                        Substitute verdict (required for override):
                      </label>
                      <select
                        id="overridden-verdict"
                        value={overriddenVerdict ?? ''}
                        onChange={(e) => setOverriddenVerdict((e.target.value as Verdict) || null)}
                        className="mt-1 min-h-target w-full border border-hairline bg-paper px-3 py-1 font-mono text-body text-ink"
                      >
                        <option value="">Select substituted verdict</option>
                        <option value="PASS">PASS</option>
                        <option value="REVIEW">REVIEW</option>
                        <option value="POTENTIAL_VIOLATION">POTENTIAL VIOLATION</option>
                      </select>
                      {!overriddenVerdict && (
                        <p className="mt-1 font-mono text-label text-seal">
                          * An override must state the substitute recommendation verdict.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Note input */}
                  <div>
                    <label htmlFor="review-note" className="block text-label text-hairline">
                      Officer note {selectedAction === 'confirm' ? '(optional)' : '(required)'}:
                    </label>
                    <input
                      id="review-note"
                      type="text"
                      placeholder={
                        selectedAction === 'override'
                          ? 'State why the recommended verdict is being overridden...'
                          : selectedAction === 'reject'
                            ? 'State reason for rejection...'
                            : selectedAction === 'confirm'
                              ? 'Optional notes on confirmation...'
                              : 'Enter notes...'
                      }
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      className="mt-1 min-h-target w-full border border-hairline bg-paper px-3 py-1.5 text-body text-ink placeholder:text-mute"
                    />
                    {selectedAction !== 'confirm' && !reviewNote.trim() && (
                      <p className="mt-1 font-mono text-label text-seal">
                        * A text note explaining the decision is required for action: {selectedAction}.
                      </p>
                    )}
                  </div>

                  {/* Offline / Submission Error banner with retry affordance (Requirement 7) */}
                  {reviewError && (
                    <div className="border-2 border-seal bg-paper p-3 text-ink" role="alert">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-seal">{reviewError}</p>
                          <p className="mt-0.5 text-secondary text-mute">
                            Backend is offline or unreachable. Review action could not be recorded on the server.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => handleReviewSubmit(e as unknown as React.FormEvent)}
                          disabled={submittingReview}
                          className="min-h-target border border-ink bg-paper px-4 py-1.5 font-mono text-label text-ink hover:bg-mute/10 active:bg-mute/20"
                        >
                          Retry submission
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedAction(null)
                        setReviewError(null)
                      }}
                      className="min-h-target px-3 py-1 text-label text-hairline hover:text-paper"
                    >
                      Clear selection
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitDisabled}
                      className={`min-h-target px-6 py-2 font-mono text-body font-medium transition-colors ${
                        isSubmitDisabled
                          ? 'cursor-not-allowed border border-hairline/40 bg-ink text-hairline/50'
                          : 'border border-paper bg-paper text-ink hover:bg-paper/90'
                      }`}
                    >
                      {submittingReview ? 'Submitting determination...' : 'Submit determination'}
                    </button>
                  </div>
                </div>
              )}
            </form>
          )}
        </div>
      </footer>
    </div>
  )
}

interface LedgerRowProps {
  finding: FieldFinding
  focused: boolean
  onFocus: () => void
}

function LedgerRow({ finding, focused, onFocus }: LedgerRowProps) {
  const isInsufficient = finding.state === 'INSUFFICIENT_EVIDENCE'

  return (
    <li
      className={`border-b border-hairline border-l-5 transition-colors duration-150 ${
        focused ? 'border-l-ink bg-focus-tint' : 'border-l-transparent bg-paper'
      }`}
    >
      <button
        type="button"
        onClick={onFocus}
        onFocus={onFocus}
        aria-current={focused ? 'true' : undefined}
        className="flex min-h-target w-full flex-col items-stretch gap-3 px-4 py-4 text-left sm:px-5"
      >
        <span className="flex flex-wrap items-start justify-between gap-3">
          <span className="text-body font-medium">{rowLabel(finding)}</span>
          <FieldStateChip state={finding.state as FieldState} />
        </span>

        <span className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <MeasuredPair observed={finding.observed_value ?? null} expected={finding.expected_value ?? null} />
          <span className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <span className="text-label text-mute">Rule</span>
            <span className="font-mono text-secondary text-ink">
              {finding.rule_snapshot?.clause_ref ?? '—'}
            </span>
            <span className="text-label text-mute">Evidence</span>
            <span className="font-mono text-secondary text-ink">
              {finding.evidence_span_ids.length > 0
                ? `${finding.evidence_span_ids.length} span${finding.evidence_span_ids.length === 1 ? '' : 's'}`
                : 'None'}
            </span>
          </span>
        </span>

        <span className="text-secondary text-mute">{finding.reason}</span>
      </button>

      {isInsufficient && (
        <div className="px-4 pb-4 sm:px-5">
          <button
            type="button"
            className="inline-flex min-h-target w-full items-center justify-center gap-2 bg-ink px-4 py-2 text-label text-paper focus-visible:outline-paper sm:w-auto"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
              <path
                d="M2.6 8a5.4 5.4 0 1 1 1.7 3.9"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
              />
              <path
                d="M1.6 13.4V9.6h3.8"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Request recapture
          </button>
        </div>
      )}
    </li>
  )
}