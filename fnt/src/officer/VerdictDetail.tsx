import { useMemo, useState } from 'react'
import { FieldState, type ExtractedSpan, type FieldFinding } from '../fixtures/contracts'
import {
  captureContext,
  spans,
  verdictRecord,
} from '../fixtures/verdict-detail.fixture'
import { CapturePlate } from './components/CapturePlate'
import { FieldStateChip } from './components/FieldStateChip'
import { VerdictBanner } from './components/VerdictBanner'

/**
 * Verdict detail. Phone 390 first, desktop 1280 second — the inspector is
 * standing up.
 *
 * The screen opens with the INSUFFICIENT EVIDENCE row focused. That row is the
 * most important thing in the product: it is the system declining to produce a
 * millimetre figure it cannot justify, and it is meant to read as a decision
 * rather than as a failure.
 */

/**
 * Row labels, keyed by declaration and clause. Not derived: two findings here
 * are about the net quantity declaration under different rules, and a derived
 * label would have to guess which reading of "net quantity" each one means.
 */
const ROW_LABELS: Record<string, string> = {
  'NET_QUANTITY|Rule 7(2) Table-I': 'Net quantity, letter height',
  'UNIT_SALE_PRICE|Rule 6(11)': 'Unit sale price basis',
  'NAME_AND_ADDRESS|Rule 6(1)(a)': 'Manufacturer name and address',
  'NET_QUANTITY|Rule 8(1)': 'Free space around the quantity declaration',
  'COUNTRY_OF_ORIGIN|Rule 6(1)(aa)': 'Country of origin',
  'RETAIL_SALE_PRICE|Rule 7(2) Table-I': 'Retail sale price, letter height',
}

function rowLabel(finding: FieldFinding): string {
  const key = `${finding.field}|${finding.rule_snapshot.clause_ref}`
  return ROW_LABELS[key] ?? finding.field
}

/**
 * Reading confidence for a row: the lowest across the spans it cites. A row
 * that cites no spans has none, and shows none — the machine makes no claim
 * about a reading it did not make.
 */
function rowConfidence(cited: readonly ExtractedSpan[]): number | null {
  if (cited.length === 0) return null
  return cited.reduce((lowest, span) => Math.min(lowest, span.confidence), 1)
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Kolkata',
  }).format(date)
}

/**
 * Permanent furniture, not a toast. An officer must never have to remember
 * whether they saw an offline warning three minutes ago.
 */
function Masthead() {
  return (
    <header className="sticky top-0 z-10 border-b-2 border-ink bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 py-2 lg:flex lg:items-baseline lg:gap-6 lg:py-3">
        <div className="flex items-center justify-between gap-4 lg:contents">
          <span className="text-label text-mute lg:order-1">PCCS</span>
          {/*
           * Permanent furniture. Two channels — the slashed-circle mark and
           * the word — and never a colour dot. It carries the consequence, not
           * just the status: what an officer needs to know is where the
           * findings are sitting, not that a radio is down.
           */}
          <span className="flex shrink-0 items-center gap-2 border border-ink px-2 py-0.5 lg:order-3 lg:ml-auto">
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.75" />
              <path d="M3.8 12.2 12.2 3.8" stroke="currentColor" strokeWidth="1.75" />
            </svg>
            <span className="font-mono text-label">
              {captureContext.online ? 'Online' : 'Offline — findings held on device'}
            </span>
          </span>
        </div>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-0.5 lg:order-2 lg:mt-0 lg:gap-x-6">
          <MastheadValue label="Inspection" value={captureContext.inspectionId} />
          <MastheadValue label="Rule set" value={verdictRecord.rule_set_version} />
          <MastheadValue label="Captured" value={formatTimestamp(captureContext.capturedAt)} />
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

/** A machine-side measured/required pair, set in mono so digits align. */
function MeasuredPair({ observed, expected }: { observed: string | null; expected: string | null }) {
  if (observed === null && expected === null) {
    return <span className="text-secondary text-mute">No measurement taken.</span>
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
  const spansById = useMemo(
    () => new Map(spans.map((span) => [span.span_id, span])),
    [],
  )

  /*
   * Opens on the INSUFFICIENT EVIDENCE row. Found by state rather than by
   * index, so the fixture can be reordered without silently changing which row
   * the officer lands on.
   */
  const initialIndex = useMemo(() => {
    const index = verdictRecord.findings.findIndex(
      (finding) => finding.state === FieldState.INSUFFICIENT_EVIDENCE,
    )
    return index === -1 ? 0 : index
  }, [])

  const [focusedIndex, setFocusedIndex] = useState(initialIndex)
  const focused = verdictRecord.findings[focusedIndex]

  const pinnedSpans = useMemo(() => {
    if (!focused) return []
    return focused.evidence_span_ids
      .map((id) => spansById.get(id))
      .filter((span): span is ExtractedSpan => span !== undefined)
  }, [focused, spansById])

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Masthead />

      <main className="mx-auto max-w-[1280px] px-4 pb-40 lg:pb-32">
        <h1 className="sr-only">Verdict detail for {verdictRecord.subject_ref}</h1>

        <div className="lg:grid lg:grid-cols-[1fr_400px] lg:gap-10">
          <div className="min-w-0">
            <div className="pt-6">
              <VerdictBanner verdict={verdictRecord.verdict} />
            </div>

            {/* The capture sits between the verdict and the ledger on a phone,
                where there is no room for a second column. On desktop it moves
                into its own register on the right. */}
            <div className="mt-6 lg:hidden">
              <CapturePlate
                pinnedSpans={pinnedSpans}
                showUnresolvedRegion={focused?.state === FieldState.INSUFFICIENT_EVIDENCE}
                inspectionId={captureContext.inspectionId}
              />
            </div>

            <h2 className="mt-8 text-section">Findings</h2>
            <ul className="m-0 mt-3 list-none border-t border-hairline p-0">
              {verdictRecord.findings.map((finding, index) => (
                <LedgerRow
                  key={`${finding.field}-${finding.rule_snapshot.rule_id}`}
                  finding={finding}
                  confidence={rowConfidence(
                    finding.evidence_span_ids
                      .map((id) => spansById.get(id))
                      .filter((span): span is ExtractedSpan => span !== undefined),
                  )}
                  focused={index === focusedIndex}
                  onFocus={() => setFocusedIndex(index)}
                />
              ))}
            </ul>
          </div>

          <aside className="hidden lg:block lg:pt-6">
            <div className="lg:sticky lg:top-24">
              <CapturePlate
                pinnedSpans={pinnedSpans}
                showUnresolvedRegion={focused?.state === FieldState.INSUFFICIENT_EVIDENCE}
                inspectionId={captureContext.inspectionId}
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
  confidence: number | null
  focused: boolean
  onFocus: () => void
}

/**
 * One ruled row. No card, no shadow: a ledger is a ruled document, and a row
 * that lifts off the page is a card pretending to be a row.
 *
 * Focus is a 4px ink left bar plus a shift to the focus tint. Because unfilled
 * state chips carry their own Field Paper ground, the tint never lands under a
 * state colour — see DESIGN.md on the ochre measurement.
 */
function LedgerRow({ finding, confidence, focused, onFocus }: LedgerRowProps) {
  const isInsufficient = finding.state === FieldState.INSUFFICIENT_EVIDENCE

  return (
    <li
      className={`border-b border-hairline border-l-5 transition-colors duration-150 ${
        focused ? 'border-l-ink bg-focus-tint' : 'border-l-transparent bg-paper'
      }`}
    >
      {/* Selecting by focus as well as by click: tabbing through the ledger
          pins each row's evidence as the officer reaches it, which is what
          "row focus pins its polygon" has to mean on a keyboard. */}
      <button
        type="button"
        onClick={onFocus}
        onFocus={onFocus}
        aria-current={focused ? 'true' : undefined}
        className="flex w-full min-h-target flex-col items-stretch gap-3 px-4 py-4 text-left sm:px-5"
      >
        <span className="flex flex-wrap items-start justify-between gap-3">
          <span className="text-body font-medium">{rowLabel(finding)}</span>
          <FieldStateChip state={finding.state} />
        </span>

        <span className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <MeasuredPair observed={finding.observed_value} expected={finding.expected_value} />
          <span className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <span className="text-label text-mute">Rule</span>
            <span className="font-mono text-secondary text-ink">
              {finding.rule_snapshot.clause_ref}
            </span>
            <span className="text-label text-mute">Confidence</span>
            <span className="font-mono text-secondary text-ink">
              {confidence === null ? (
                <>
                  <span aria-hidden="true">—</span>
                  <span className="sr-only">No confidence claim: no reading was made.</span>
                </>
              ) : (
                confidence.toFixed(2)
              )}
            </span>
          </span>
        </span>

        <span className="text-secondary text-mute">{finding.reason}</span>
      </button>

      {/*
       * The remedy is the fastest-read channel on the row, and it tells the
       * officer which state they are looking at before the label does.
       * INSUFFICIENT EVIDENCE always offers recapture; FAIL never does —
       * re-photographing a package that genuinely falls short of a rule does
       * not change what the package says.
       *
       * A real button, and a sibling of the row rather than a child of it:
       * nesting it inside the row button would make it unreachable by keyboard
       * and invalid markup besides.
       */}
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

/**
 * The officer's column. It never shares a background with the machine's: what
 * the system found sits on Field Paper, what the officer decides sits on
 * Gazette Ink, and a heavy rule divides them. Fixed to the bottom of the
 * viewport on a phone, at thumb reach.
 */
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
