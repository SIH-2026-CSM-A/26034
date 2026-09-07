import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { CapturePlate } from './components/CapturePlate'
import { FieldStateChip } from './components/FieldStateChip'
import { VerdictBanner } from './components/VerdictBanner'

type ScanDetail = components['schemas']['ScanDetail']
type FieldFinding = components['schemas']['FieldFinding']
type FieldState = components['schemas']['FieldState']

const ROW_LABELS: Partial<Record<string, string>> = {
  'NET_QUANTITY|Rule 7(2), Table-I': 'Net quantity, letter height',
  'UNIT_SALE_PRICE|Rule 6(11)': 'Unit sale price basis',
  'NAME_AND_ADDRESS|Rule 6(1)(a)': 'Manufacturer name and address',
  'NET_QUANTITY|Rule 8(1) proviso': 'Free space around the quantity declaration',
  'COUNTRY_OF_ORIGIN|Rule 6(1)(aa)': 'Country of origin',
  'RETAIL_SALE_PRICE|Rule 7(2), Table-I': 'Retail sale price, letter height',
}

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

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Masthead
        inspectionId={scan.id}
        ruleSetVersion={scan.rule_set_version}
        capturedAt={scan.created_at}
        isOnline={!error}
      />

      <main className="mx-auto max-w-[1280px] px-4 pb-40 lg:pb-32">
        <h1 className="sr-only">Verdict detail for {scan.id}</h1>

        <div className="lg:grid lg:grid-cols-[1fr_400px] lg:gap-10">
          <div className="min-w-0">
            <div className="pt-6">
              {scan.verdict ? (
                <VerdictBanner verdict={scan.verdict} />
              ) : (
                <div className="border border-dashed border-mute p-4">
                  <span className="font-mono text-label text-mute">Status: {scan.status.toUpperCase()}</span>
                  <p className="mt-1 text-secondary text-mute">No recommendation verdict issued.</p>
                </div>
              )}
            </div>

            {/* Category classification & proposal block (UI Rule 3) */}
            <section aria-label="Category classification" className="mt-6 border border-hairline bg-paper p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-label text-mute">Confirmed Category</span>
                <span className="font-mono text-body font-medium">
                  {scan.product_category ? scan.product_category.toUpperCase() : 'None (Unconfirmed)'}
                </span>
              </div>

              <div className="mt-3 border-t border-hairline pt-3">
                <span className="text-label text-mute">Category Proposal</span>
                {scan.category_proposal ? (
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
                      {scan.category_proposal.category}
                    </p>
                    <p className="mt-1 text-secondary text-mute">
                      Confidence: {(scan.category_proposal.confidence * 100).toFixed(0)}% • {scan.category_proposal.reason}
                    </p>
                  </div>
                ) : (
                  <p className="mt-1 font-mono text-secondary text-mute">
                    None — no category proposal recorded
                  </p>
                )}
              </div>
            </section>

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

      <OfficerActions />
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

function OfficerActions() {
  return (
    <div className="sticky bottom-0 border-t-8 border-double border-ink bg-ink">
      <div className="mx-auto flex max-w-[1280px] flex-wrap gap-2 px-4 py-3">
        <p className="w-full text-label text-hairline">Officer action</p>
        <OfficerAction label="Confirm" primary />
        <OfficerAction label="Override" />
        <OfficerAction label="Annotate" />
        <OfficerAction label="Request recapture" />
      </div>
    </div>
  )
}

function OfficerAction({ label, primary = false }: { label: string; primary?: boolean }) {
  return (
    <button
      type="button"
      className={`min-h-target flex-1 whitespace-nowrap px-4 py-2 text-body focus-visible:outline-paper ${
        primary
          ? 'bg-paper font-medium text-ink'
          : 'border border-hairline bg-ink font-normal text-paper'
      }`}
    >
      {label}
    </button>
  )
}