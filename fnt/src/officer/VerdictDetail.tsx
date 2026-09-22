import { SEEDED_DEMO_OFFICER } from '../services/demo'
import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { serverMessage, thrownMessage } from '../services/errors'
import type { components } from '../services/generated/schema'
import { FieldStateChip } from './components/FieldStateChip'
import { Notice } from '../ui/Notice'
import { rise, spring, stagger } from '../ui/motion'
import { VerdictBanner, verdictLabel } from './components/VerdictBanner'

type ScanDetail = components['schemas']['ScanDetail']
type ScanSummary = components['schemas']['ScanSummary']
type FieldFinding = components['schemas']['FieldFinding']
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
  // The reader never proposes this one — there is no licence line to read it off — so
  // the control has to offer it, or a non-consumable can never be confirmed at all.
  { value: 'non_consumable', label: 'Non-consumable' },
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
    <header className="glass sticky top-0 z-30 border-b border-hairline/60">
      <div className="mx-auto max-w-[1280px] px-4 py-2 lg:flex lg:items-baseline lg:gap-6 lg:py-3">
        <div className="flex items-center justify-between gap-4 lg:contents">
          <Link
            to="/officer/queue"
            className="-ml-2 flex min-h-target items-center gap-1 rounded-ctl px-2 text-secondary font-medium text-ink lg:order-1"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
              <path d="M10 3.5 5.5 8l4.5 4.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Queue
          </Link>
          <span className="flex shrink-0 items-center gap-2 rounded-full border border-hairline bg-surface px-3 py-1 lg:order-3 lg:ml-auto">
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

/** What the hero needs, and all of it is on a queue row as well as on the full record. */
type ScanHead = Pick<ScanSummary, 'id' | 'verdict' | 'status' | 'officer_id'>

/**
 * The shared element. A queue row carries layoutId `scan-<id>` and so does this, so
 * the row grows into the verdict. The queue hands its row over in router state, which
 * puts the verdict on screen on the first frame instead of after the detail fetch.
 */
function Hero({ scan }: { scan: ScanHead }) {
  return (
    <motion.div layoutId={`scan-${scan.id}`} transition={spring.glide} className="rounded-card">
      {scan.verdict ? (
        <div>
          <VerdictBanner verdict={scan.verdict} />
          {scan.officer_id === SEEDED_DEMO_OFFICER && (
            <p className="badge-seeded mt-3 rounded-ctl px-3 py-1.5 text-label">
              Seeded demo record: this scan was entered to populate the demonstration, not collected in the field.
            </p>
          )}
          <p className="mt-2 text-label text-mute">
            Recommendation only. Official determination requires officer review.
          </p>
        </div>
      ) : (
        <div className="rounded-card border-2 border-dotted border-mute bg-surface p-5">
          <span className="font-mono text-label text-mute">Status: {scan.status.toUpperCase()}</span>
          <p className="mt-1 text-secondary text-mute">No recommendation verdict issued.</p>
        </div>
      )}
    </motion.div>
  )
}

/** Ledger-shaped placeholder: same row anatomy as LedgerRow, so the findings land in place. */
function LedgerSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading findings">
      <div className="skeleton mt-8 h-6 w-28" />
      <div className="card mt-3 divide-y divide-hairline/70 overflow-hidden">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="space-y-3 px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <span className="skeleton h-5 w-2/5" />
              <span className="skeleton h-7 w-24 rounded-full" />
            </div>
            <span className="skeleton block h-4 w-3/5" />
            <span className="skeleton block h-4 w-4/5" />
          </div>
        ))}
      </div>
    </div>
  )
}

/** Deliberately unordered by preference: nothing is pre-selected and nothing is styled as the default. */
const DISPOSITIONS: ReadonlyArray<{ action: ReviewAction; label: string }> = [
  { action: 'confirm', label: 'Confirm' },
  { action: 'override', label: 'Override' },
  { action: 'reject', label: 'Reject' },
  { action: 'annotate', label: 'Annotate' },
  { action: 'request_recapture', label: 'Request recapture' },
]

export function VerdictDetail() {
  const { subjectRef } = useParams<{ subjectRef: string }>()
  const navigate = useNavigate()
  const handedOver = (useLocation().state as { summary?: ScanSummary } | null)?.summary
  const summary = handedOver && handedOver.id === subjectRef ? handedOver : null
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [focusedIndex, setFocusedIndex] = useState(0)

  // Category confirmation (UI Rule 4). `scan.product_category` is the officer's confirmed
  // answer as the server holds it; this is only what the select currently shows.
  const [pendingCategory, setPendingCategory] = useState<ProductCategory | ''>('')
  const [confirmingCategory, setConfirmingCategory] = useState(false)
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const noteRef = useRef<HTMLInputElement>(null)

  // Officer Confirmation Surface State (UI Rule 1: NO pre-selection)
  const [selectedAction, setSelectedAction] = useState<ReviewAction | null>(null)
  const [overriddenVerdict, setOverriddenVerdict] = useState<Verdict | null>(null)
  const [reviewNote, setReviewNote] = useState<string>('')
  const [submittingReview, setSubmittingReview] = useState<boolean>(false)
  const [reviewError, setReviewError] = useState<string | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null)
  // The determination sheet starts as a bar so the findings can be read first. Opening it selects nothing.
  const [sheetOpen, setSheetOpen] = useState(false)

  const fetchScan = useCallback(async () => {
    if (!subjectRef) {
      setError('No inspection reference provided.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data, error: apiError, response } = await apiClient.GET('/scans/{scan_id}', {
        params: {
          path: { scan_id: subjectRef },
        },
      })

      if (apiError || !data) {
        setError(serverMessage(apiError, response))
        setScan(null)
      } else {
        setScan(data)
        setError(null)
        setPendingCategory((data.product_category as ProductCategory | null) ?? '')
        const insufficientIdx = data.findings.findIndex(
          (f) => f.state === 'INSUFFICIENT_EVIDENCE',
        )
        setFocusedIndex(insufficientIdx === -1 ? 0 : insufficientIdx)
      }
    } catch (err) {
      setError(thrownMessage(err))
      setScan(null)
    } finally {
      setLoading(false)
    }
  }, [subjectRef])

  /**
   * `POST /scans/{id}/category`: the officer's answer, evaluated again as a **new** scan.
   * The original stays as it was, so the page moves to the scan that carries the
   * confirmed category; nothing the reader proposed is consulted on the way.
   */
  const confirmCategory = useCallback(
    async (category: ProductCategory) => {
      if (!scan) return
      setConfirmingCategory(true)
      setCategoryError(null)
      try {
        const { data, error: apiError, response } = await apiClient.POST('/scans/{scan_id}/category', {
          params: { path: { scan_id: scan.id } },
          body: { product_category: category },
        })
        if (apiError || !data) {
          setCategoryError(serverMessage(apiError, response))
          return
        }
        navigate(`/officer/verdicts/${data.id}`)
      } catch (err) {
        setCategoryError(thrownMessage(err))
      } finally {
        setConfirmingCategory(false)
      }
    },
    [scan, navigate],
  )

  /** A ledger row asked for a recapture: open the sheet on that disposition, cursor in the note. */
  const requestRecapture = useCallback(() => {
    setSelectedAction('request_recapture')
    setSheetOpen(true)
    window.setTimeout(() => noteRef.current?.focus(), 250)
  }, [])

  useEffect(() => {
    fetchScan()
  }, [fetchScan])

  const findings = scan?.findings ?? []

  // UI Rule 3: Insufficient evidence visibility.
  //
  // Counted by DECLARATION, not by finding. Each declaration is governed by several rules
  // — the Rule 6 declaration itself, then height, width, placement, free space, contrast —
  // so one pack produced 66 findings over 11 declarations and this banner called 58 of them
  // "58 DECLARATIONS" on a package that has eleven. A number an officer reads off a sheet
  // about one package has to be a number of things on that package.
  const insufficientFindings = findings.filter((f) => f.state === 'INSUFFICIENT_EVIDENCE')
  const insufficientFields = [...new Set(insufficientFindings.map((f) => f.field))]
  const declarationCount = new Set(findings.map((f) => f.field)).size
  const unreadSummary =
    insufficientFields.length === 1
      ? '1 declaration'
      : `${insufficientFields.length} of ${declarationCount} declarations`

  // What actually produced the recommendation. Only a FAIL reaches POTENTIAL VIOLATION: a
  // FAIL is a statement about the package, and insufficient evidence is a statement about
  // our reading of it. Naming the FAIL findings is what stops the two being read as cause
  // and effect when they sit one above the other on this sheet.
  const failFindings = findings.filter((f) => f.state === 'FAIL')
  const failClauses = [
    ...new Set(failFindings.map((f) => f.rule_snapshot?.clause_ref).filter(Boolean)),
  ]

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
      const { data, error: apiError, response } = await apiClient.POST(
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
        setReviewError(serverMessage(apiError, response))
      } else {
        setReviewResult(data)
        setReviewError(null)
      }
    } catch (err) {
      setReviewError(thrownMessage(err))
    } finally {
      setSubmittingReview(false)
    }
  }

  if (loading) {
    return (
      <div className="aurora">
        {summary ? (
          <Masthead
            inspectionId={summary.id}
            ruleSetVersion={summary.rule_set_version}
            capturedAt={summary.created_at}
            isOnline
          />
        ) : (
          <header className="glass sticky top-0 z-30 border-b border-hairline/60 px-4 py-3">
            <span className="text-label text-mute">PCCS Inspection</span>
          </header>
        )}
        <main className="mx-auto max-w-[1280px] px-4 pb-48">
          <div className="max-w-3xl pt-6">
            {summary ? <Hero scan={summary} /> : <div aria-hidden="true" className="skeleton h-[136px] rounded-card" />}
            <LedgerSkeleton />
          </div>
        </main>
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="aurora">
        <header className="glass sticky top-0 z-30 border-b border-hairline/60 px-4 py-1.5">
          <Link to="/officer/queue" className="flex min-h-target items-center text-secondary font-medium text-ink">
            ← Back to queue
          </Link>
        </header>
        <main className="mx-auto max-w-3xl p-4 pt-6">
          <Notice
            title="Unable to load inspection"
            role="alert"
            action={
              <button type="button" onClick={fetchScan} className="btn btn-quiet">
                Retry
              </button>
            }
          >
            <span className="font-mono">{error ?? 'Scan not found'}</span>
          </Notice>
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
    <div className="aurora">
      <Masthead
        inspectionId={scan.id}
        ruleSetVersion={scan.rule_set_version}
        capturedAt={scan.created_at}
        isOnline={!error}
      />

      <main className="mx-auto max-w-[1280px] px-4 pb-32">
        <h1 className="sr-only">Verdict detail for {scan.id}</h1>

        <div className="max-w-3xl">
          <div className="min-w-0">
            {/* Recommendation verdict banner (UI Rule 2) */}
            <div className="pt-6">
              <Hero scan={scan} />
            </div>

            {/* Category confirmation control (UI Rule 4) */}
            <section aria-label="Category classification" className="card mt-6 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <span className="text-label text-mute">Confirmed Product Category</span>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2">
                    <p className="font-mono text-body font-semibold">
                      {scan.product_category ? scan.product_category.toUpperCase() : 'None (Unconfirmed)'}
                    </p>
                    {scan.product_category ? (
                      <span className="rounded-full border border-ink/40 px-2 py-0.5 font-mono text-label text-ink">
                        OFFICER CONFIRMED
                      </span>
                    ) : (
                      <span className="rounded-full border border-dashed border-mute px-2 py-0.5 font-mono text-label text-mute">
                        AWAITING OFFICER CONFIRMATION
                      </span>
                    )}
                  </div>
                  <p className="mt-1 max-w-[60ch] text-label text-mute">
                    Rule 7, 8 and 9 findings stay at INSUFFICIENT_EVIDENCE until an officer confirms the
                    category. Confirming evaluates the held capture again as a new scan; this one is
                    left as it was.
                  </p>
                </div>
                <div className="flex flex-wrap items-end gap-2">
                  <div>
                    <label htmlFor="select-category" className="block text-label text-mute">
                      {scan.product_category ? 'Correct to' : 'Confirm as'}
                    </label>
                    <select
                      id="select-category"
                      value={pendingCategory}
                      onChange={(e) => setPendingCategory(e.target.value as ProductCategory | '')}
                      disabled={confirmingCategory || scan.finalised}
                      className="input mt-1 w-auto font-mono text-label"
                    >
                      <option value="">Choose a category</option>
                      {PRODUCT_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => pendingCategory && confirmCategory(pendingCategory)}
                    disabled={
                      !pendingCategory ||
                      pendingCategory === scan.product_category ||
                      confirmingCategory ||
                      scan.finalised
                    }
                    className="btn btn-primary font-mono text-label"
                  >
                    {confirmingCategory ? 'Re-evaluating…' : 'Confirm and re-evaluate'}
                  </button>
                </div>
              </div>
              {scan.finalised && (
                <p className="mt-2 text-label text-mute">
                  This scan's review is finalised. Its category cannot be changed on this row.
                </p>
              )}
              {categoryError && (
                <div className="mt-3">
                  <Notice role="alert" title="The category was not confirmed">
                    <span className="font-mono">{categoryError}</span>
                  </Notice>
                </div>
              )}

              <div className="mt-4 border-t border-hairline pt-3">
                <span className="text-label text-mute">Reader Category Proposal</span>
                {scan.category_proposal ? (
                  <div className="mt-2 rounded-ctl border border-dashed border-query bg-query-tint/40 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-query px-2 py-0.5 font-mono text-label font-medium text-query">
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
                              className="rounded-full border border-hairline bg-surface px-2 py-0.5 font-mono text-label text-ink"
                            >
                              {spanId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="mt-3.5 flex flex-wrap items-center gap-2">
                      {scan.product_category === scan.category_proposal.category ? (
                        <span className="font-mono text-label text-ink">✓ Confirmed as proposed</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => confirmCategory(scan.category_proposal!.category)}
                          disabled={confirmingCategory || scan.finalised}
                          className="btn btn-quiet font-mono text-label"
                        >
                          Confirm proposal: {scan.category_proposal.category}
                        </button>
                      )}
                      {scan.product_category && scan.product_category !== scan.category_proposal.category && (
                        <span className="font-mono text-label text-query">
                          (Corrected to {scan.product_category.toUpperCase()})
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
               <section aria-label="Evidence status" className="mt-6 rounded-card border-2 border-dotted border-mute bg-surface p-5">
                 <div className="flex flex-wrap items-center gap-2">
                   <span className="inline-block h-3 w-3 shrink-0 rounded-full border-2 border-mute" />
                   <span className="font-mono text-label font-semibold text-ink">
                     INSUFFICIENT EVIDENCE DETECTED
                   </span>
                   <span className="text-label text-mute">
                     ({unreadSummary} not fully read, across {insufficientFindings.length} rule{insufficientFindings.length === 1 ? '' : 's'})
                   </span>
                 </div>
                 <p className="mt-2 text-secondary text-mute">
                   The automated reader could not obtain readable evidence for every rule applied to these declarations. Confirming this scan acknowledges unreadable evidence, not compliance. Consider whether recapture is required.
                 </p>
                 <p className="mt-2 text-secondary text-mute">
                   {failFindings.length > 0
                     ? `Unreadable evidence did not produce the recommendation. Only a shortfall found against a legible declaration can, and this scan has ${failFindings.length}: ${failClauses.join(', ')}.`
                     : 'Nothing here is a shortfall. Unreadable evidence cannot produce a potential violation on its own — only a finding against a legible declaration can.'}
                 </p>
               </section>
            )}

            {scan.quality && (
              <div className="mt-6 rounded-card border-2 border-dotted border-mute bg-surface p-5">
                <span className="text-label font-medium text-mute">Capture Quality Note</span>
                <p className="mt-1 text-body">{scan.quality.instruction}</p>
                <p className="mt-1 font-mono text-label text-mute">Reason code: {scan.quality.reason_code}</p>
              </div>
            )}

            {/* Findings ledger */}
            <h2 className="mt-8 text-section">Findings</h2>
            {findings.length === 0 ? (
              <div className="mt-4">
                <Notice title="No rule findings evaluated for this inspection." />
              </div>
            ) : (
              <motion.ul
                variants={stagger}
                initial="hidden"
                animate="shown"
                className="card m-0 mt-3 list-none divide-y divide-hairline/70 overflow-hidden p-0"
              >
                {findings.map((finding, index) => (
                  <LedgerRow
                    key={`${finding.field}-${finding.rule_snapshot?.rule_id ?? index}`}
                    finding={finding}
                    focused={index === focusedIndex}
                    onFocus={() => setFocusedIndex(index)}
                    onRequestRecapture={scan.finalised || reviewResult ? undefined : requestRecapture}
                  />
                ))}
              </motion.ul>
            )}
          </div>
        </div>
      </main>

      {/* Officer Confirmation Control Surface */}
      <footer className="fixed inset-x-0 bottom-0 z-20 mx-auto max-h-[72vh] max-w-[1280px] overflow-y-auto rounded-t-sheet bg-ink text-paper shadow-e3 lg:inset-x-4">
        <div className="px-4 pb-[max(12px,env(safe-area-inset-bottom))] pt-4 sm:px-6">
          <button
            type="button"
            aria-expanded={sheetOpen}
            aria-controls="determination-sheet"
            onClick={() => setSheetOpen((open) => !open)}
            className="flex min-h-target w-full items-center justify-between gap-3 text-left"
          >
            <span className="min-w-0">
              <span className="block font-display text-body font-semibold">Officer determination</span>
              <span className="block truncate font-mono text-label text-paper/70">
                Recommendation: {scan.verdict ? verdictLabel(scan.verdict) : 'NONE'}
                {insufficientFindings.length > 0 && ` · ${unreadSummary} not fully read`}
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-2 rounded-full bg-paper px-4 py-2 text-label font-semibold text-ink">
              {sheetOpen ? 'Hide' : reviewResult ? 'View' : 'Decide'}
              <motion.svg
                viewBox="0 0 16 16"
                aria-hidden="true"
                className="h-3.5 w-3.5"
                fill="none"
                animate={{ rotate: sheetOpen ? 180 : 0 }}
                transition={spring.snap}
              >
                <path d="M3.5 10 8 5.5l4.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </motion.svg>
            </span>
          </button>
          <div id="determination-sheet" hidden={!sheetOpen} className="mt-3">
          {reviewResult ? (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={spring.glide}
              className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-surface p-4 text-ink"
            >
              <div>
                <span className="rounded-full border border-ink/40 px-2 py-0.5 font-mono text-label font-semibold text-ink">
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
                className="btn btn-quiet text-label"
              >
                Modify determination
              </button>
            </motion.div>
          ) : (
            <form onSubmit={handleReviewSubmit} className="space-y-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-mono text-label text-paper/70">
                  Officer confirmation surface • Determination step
                </p>
                <p className="text-label text-paper/70">
                  Recommendation: {scan.verdict ? verdictLabel(scan.verdict) : 'NONE'}
                  {failFindings.length > 0
                    ? ` — from ${failFindings.length} finding${failFindings.length === 1 ? '' : 's'} against a legible declaration`
                    : ' — no shortfall was found against a legible declaration'}
                </p>
              </div>

              {/* Insufficient Evidence prominent banner during confirmation (UI Rule 3) */}
              {insufficientFindings.length > 0 && (
                <div className="rounded-ctl border border-dotted border-paper/50 p-3 text-paper">
                  <div className="flex items-center gap-2">
                    <span className="inline-block h-3 w-3 shrink-0 rounded-full border-2 border-paper" />
                    <span className="font-mono text-label font-semibold text-paper">
                      INSUFFICIENT EVIDENCE · {unreadSummary.toUpperCase()} NOT FULLY READ
                    </span>
                  </div>
                  <p className="mt-1 text-label text-paper/70">
                    {insufficientFields.map((field) => field.replace(/_/g, ' ').toLowerCase()).join(', ')}.
                  </p>
                  <p className="mt-1 text-label text-paper/70">
                    Confirming records an acknowledgement of unreadable evidence, NOT compliance. Lack of evidence must not be folded into a pass state, and it did not produce the recommendation above.
                  </p>
                </div>
              )}

              {/* Action selection buttons (UI Rule 1: NO PRE-SELECTION) */}
              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="font-mono text-label text-paper/70">
                    Disposition choices (No default selected • Explicit selection required):
                  </span>
                  {selectedAction === null && (
                    <span className="font-mono text-label text-paper/80">
                      * Please select an action
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5 rounded-[18px] bg-paper/10 p-1.5">
                  {DISPOSITIONS.map(({ action, label }) => {
                    const chosen = selectedAction === action
                    return (
                      <button
                        key={action}
                        type="button"
                        aria-pressed={chosen}
                        onClick={() => setSelectedAction(chosen ? null : action)}
                        className={`relative min-h-target flex-1 whitespace-nowrap rounded-ctl px-4 text-secondary transition-[color,transform] duration-base ease-out active:scale-[0.97] ${
                          chosen ? 'font-semibold text-ink' : 'text-paper hover:bg-paper/10'
                        }`}
                      >
                        {chosen && (
                          <motion.span
                            layoutId="disposition-pill"
                            transition={spring.snap}
                            className="absolute inset-0 rounded-ctl bg-paper shadow-e2"
                          />
                        )}
                        <span className="relative">{label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Action-specific fields when an action is selected */}
              <AnimatePresence initial={false}>
              {selectedAction && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={spring.glide}
                  className="space-y-3 border-t border-paper/20 pt-3"
                >
                  {/* Notice when confirming with insufficient evidence (UI Rule 3) */}
                  {selectedAction === 'confirm' && insufficientFindings.length > 0 && (
                    <div className="rounded-ctl border border-dashed border-query bg-query-tint p-3 text-ink">
                      <p className="font-mono text-label font-bold text-query">
                        NOTICE: CONFIRMING WITH UNREADABLE EVIDENCE
                      </p>
                      <p className="mt-0.5 text-label text-ink">
                        Confirming records an explicit acknowledgement that {unreadSummary} could not be fully read. This will NOT be recorded as statutory compliance.
                      </p>
                    </div>
                  )}

                  {/* Override requires selecting overridden_verdict (UI Rule 2 & UI Rule 6) */}
                  {selectedAction === 'override' && (
                    <div>
                      <label htmlFor="overridden-verdict" className="block text-label text-paper/70">
                        Substitute verdict (required for override):
                      </label>
                      <select
                        id="overridden-verdict"
                        value={overriddenVerdict ?? ''}
                        onChange={(e) => setOverriddenVerdict((e.target.value as Verdict) || null)}
                        className="input mt-1 bg-surface font-mono"
                      >
                        <option value="">Select substituted verdict</option>
                        <option value="PASS">PASS</option>
                        <option value="REVIEW">REVIEW</option>
                        <option value="POTENTIAL_VIOLATION">POTENTIAL VIOLATION</option>
                      </select>
                      {!overriddenVerdict && (
                        <p className="mt-1 font-mono text-label text-paper/80">
                          * An override must state the substitute recommendation verdict.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Note input */}
                  <div>
                    <label htmlFor="review-note" className="block text-label text-paper/70">
                      Officer note {selectedAction === 'confirm' ? '(optional)' : '(required)'}:
                    </label>
                    <input
                      ref={noteRef}
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
                      className="input mt-1 bg-surface"
                    />
                    {selectedAction !== 'confirm' && !reviewNote.trim() && (
                      <p className="mt-1 font-mono text-label text-paper/80">
                        * A text note explaining the decision is required for action: {selectedAction}.
                      </p>
                    )}
                  </div>

                  {/* Offline / Submission Error banner with retry affordance (Requirement 7) */}
                  {reviewError && (
                    <div className="rounded-ctl border border-dashed border-hairline bg-surface p-3 text-ink" role="alert">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-ink">{reviewError}</p>
                          <p className="mt-0.5 text-secondary text-mute">
                            Backend is offline or unreachable. Review action could not be recorded on the server.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => handleReviewSubmit(e as unknown as React.FormEvent)}
                          disabled={submittingReview}
                          className="btn btn-quiet font-mono text-label"
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
                      className="btn px-3 text-label text-paper/70 hover:text-paper"
                    >
                      Clear selection
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitDisabled}
                      className="btn bg-paper px-6 font-mono font-medium text-ink shadow-e2"
                    >
                      {submittingReview ? 'Submitting determination...' : 'Submit determination'}
                    </button>
                  </div>
                </motion.div>
              )}
              </AnimatePresence>
            </form>
          )}
          </div>
        </div>
      </footer>
    </div>
  )
}

interface LedgerRowProps {
  finding: FieldFinding
  focused: boolean
  onFocus: () => void
  /** Opens the determination sheet on "request recapture"; absent once the review is finalised. */
  onRequestRecapture?: () => void
}

function LedgerRow({ finding, focused, onFocus, onRequestRecapture }: LedgerRowProps) {
  const isInsufficient = finding.state === 'INSUFFICIENT_EVIDENCE'

  return (
    <motion.li
      variants={rise}
      className={`border-l-5 transition-colors duration-base ease-out ${
        focused ? 'border-l-ink bg-focus-tint' : 'border-l-transparent bg-surface'
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
          <FieldStateChip state={finding.state} />
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

      {isInsufficient && onRequestRecapture && (
        <div className="px-4 pb-4 sm:px-5">
          <button
            type="button"
            onClick={onRequestRecapture}
            className="btn btn-primary w-full text-label sm:w-auto"
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
    </motion.li>
  )
}