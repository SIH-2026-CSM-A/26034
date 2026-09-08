import React, { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictTag } from './components/VerdictBanner'

// API-typed aliases
type ComplaintResponseAPI = components['schemas']['ComplaintResponse']
type ComplaintStatusAPI = components['schemas']['ComplaintStatus']
type ScanSummary = components['schemas']['ScanSummary']
type DeclarationField = components['schemas']['DeclarationField']

export type Verdict = 'PASS' | 'REVIEW' | 'POTENTIAL_VIOLATION'

// The server status enum uses lowercase; the UI labels use uppercase for display.
// We keep the server casing throughout to avoid mapping errors.
export type ComplaintStatus = ComplaintStatusAPI

/**
 * A complaint record as received from the API (or constructed locally for
 * append-only lifecycle transitions until the backend exposes transition endpoints).
 */
export interface ComplaintRecord {
  id: string
  scan_id: string
  verdict_id: string
  manufacturer_name: string
  issue_summary: string
  status: ComplaintStatus
  raised_by_officer_id: string
  raised_at: string
  supersedes_id: string | null
}

export interface ComplaintThread {
  thread_id: string
  latest_record: ComplaintRecord
  history: ComplaintRecord[]
  scan_id: string
  verdict_id: string
  manufacturer_name: string
  product_description: string
}

function apiRecordToRecord(r: ComplaintResponseAPI): ComplaintRecord {
  return {
    id: r.id,
    scan_id: r.scan_id,
    verdict_id: r.verdict_id,
    manufacturer_name: r.manufacturer_name,
    issue_summary: r.issue_summary,
    status: r.status,
    raised_by_officer_id: r.raised_by_officer_id,
    raised_at: r.raised_at,
    supersedes_id: r.supersedes_id ?? null,
  }
}

function buildComplaintThreads(
  records: ComplaintRecord[],
  scansList: ScanSummary[]
): ComplaintThread[] {
  const supersededIds = new Set<string>()
  for (const r of records) {
    if (r.supersedes_id) {
      supersededIds.add(r.supersedes_id)
    }
  }

  const heads = records.filter((r) => !supersededIds.has(r.id))

  return heads.map((head) => {
    const history: ComplaintRecord[] = []
    let curr: ComplaintRecord | undefined = head
    while (curr) {
      history.unshift(curr)
      if (!curr.supersedes_id) break
      const parentId: string = curr.supersedes_id
      curr = records.find((r) => r.id === parentId)
    }

    const scan = scansList.find((s) => s.id === head.scan_id)

    return {
      thread_id: history[0]?.id ?? head.id,
      latest_record: head,
      history,
      scan_id: head.scan_id,
      verdict_id: head.verdict_id,
      manufacturer_name: head.manufacturer_name,
      product_description: scan?.product_category
        ? `Category: ${scan.product_category}`
        : 'Packaged commodity',
    }
  })
}

function checkCanRaiseComplaint(
  scan_id: string,
  scansList: ScanSummary[]
): {
  allowed: boolean
  reason: string
  scan?: ScanSummary
} {
  const scan = scansList.find((s) => s.id === scan_id)
  if (!scan) {
    return {
      allowed: false,
      reason: 'Scan reference not found in inspection repository.',
    }
  }

  if (!scan.finalised) {
    return {
      allowed: false,
      reason:
        'Forbidden: Verdict has not been explicitly confirmed by an officer. Human confirmation is strictly required prior to raising a complaint.',
      scan,
    }
  }

  return {
    allowed: true,
    reason: 'Verdict has been confirmed by an officer.',
    scan,
  }
}

function formatTimestamp(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function statusLabel(status: ComplaintStatus): string {
  switch (status) {
    case 'raised':
      return 'RAISED'
    case 'acknowledged':
      return 'ACKNOWLEDGED'
    case 'resolved':
      return 'RESOLVED'
    case 'rejected':
      return 'REJECTED'
  }
}

function statusBadge(status: ComplaintStatus) {
  switch (status) {
    case 'raised':
      return (
        <span className="inline-flex items-center border border-dashed border-query bg-paper px-2 py-0.5 font-mono text-label font-medium text-query">
          RAISED
        </span>
      )
    case 'acknowledged':
      return (
        <span className="inline-flex items-center border border-solid border-mute bg-paper px-2 py-0.5 font-mono text-label font-medium text-mute">
          ACKNOWLEDGED
        </span>
      )
    case 'resolved':
      return (
        <span className="inline-flex items-center border border-solid border-attest bg-paper px-2 py-0.5 font-mono text-label font-medium text-attest">
          ✓ RESOLVED
        </span>
      )
    case 'rejected':
      return (
        <span className="inline-flex items-center border border-solid border-seal bg-paper px-2 py-0.5 font-mono text-label font-medium text-seal">
          ✕ REJECTED
        </span>
      )
  }
}

const DECLARATION_FIELDS: DeclarationField[] = [
  'NAME_AND_ADDRESS',
  'COUNTRY_OF_ORIGIN',
  'COMMON_OR_GENERIC_NAME',
  'NET_QUANTITY',
  'MANUFACTURE_DATE',
  'BEST_BEFORE_DATE',
  'RETAIL_SALE_PRICE',
  'DIMENSIONS',
  'OTHER_PRESCRIBED_MATTER',
  'CONSUMER_CARE',
  'UNIT_SALE_PRICE',
]

export function ComplaintTracking() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Server-fetched records merged with any local append-only transitions
  const [records, setRecords] = useState<ComplaintRecord[]>([])
  const [scans, setScans] = useState<ScanSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const [statusFilter, setStatusFilter] = useState<ComplaintStatus | 'ALL'>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  // Load complaints and scans in parallel
  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      setFetchError(null)
      try {
        const [complaintsResult, scansResult] = await Promise.all([
          apiClient.GET('/complaints'),
          apiClient.GET('/scans'),
        ])
        if (!active) return

        if (complaintsResult.error || !complaintsResult.data) {
          setFetchError('Could not load complaints. Check your connection or try again.')
        } else {
          setRecords(complaintsResult.data.map(apiRecordToRecord))
        }
        if (scansResult.data && !scansResult.error) {
          setScans(scansResult.data)
        }
      } catch {
        if (active) setFetchError('Network error loading complaints.')
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [])

  // Modals & Flows
  const [activeThread, setActiveThread] = useState<ComplaintThread | null>(null)
  const [isRaiseModalOpen, setIsRaiseModalOpen] = useState(false)
  const [reopenTarget, setReopenTarget] = useState<ComplaintRecord | null>(null)
  const [transitionTarget, setTransitionTarget] = useState<{
    record: ComplaintRecord
    toStatus: 'acknowledged' | 'resolved' | 'rejected'
  } | null>(null)

  // Raise Form State
  const [selectedScanId, setSelectedScanId] = useState<string>('')
  const [manufacturerName, setManufacturerName] = useState<string>('')
  const [ruleId, setRuleId] = useState<string>('')
  const [field, setField] = useState<DeclarationField>('NET_QUANTITY')
  const [measuredValue, setMeasuredValue] = useState<string>('')
  const [requiredValue, setRequiredValue] = useState<string>('')
  const [raiseFormError, setRaiseFormError] = useState<string | null>(null)
  const [raiseSubmitting, setRaiseSubmitting] = useState(false)

  // Transition & Reopen form inputs
  const [actionNote, setActionNote] = useState<string>('')
  const [reopenJustification, setReopenJustification] = useState<string>('')
  const [reopenError, setReopenError] = useState<string | null>(null)

  // Derive threads from records and live scans
  const threads = useMemo(() => buildComplaintThreads(records, scans), [records, scans])

  // Only CONFIRMED scans can have complaints raised against them (UI Rule 1)
  const confirmedEligibleSubmissions = useMemo(() => {
    return scans.filter(
      (s) => s.finalised === true && (s.verdict === 'POTENTIAL_VIOLATION' || s.verdict === 'REVIEW')
    )
  }, [scans])

  // Handle raise_scan_id query param
  useEffect(() => {
    const raiseScanId = searchParams.get('raise_scan_id')
    if (raiseScanId) {
      const eligibility = checkCanRaiseComplaint(raiseScanId, scans)
      if (eligibility.allowed && eligibility.scan) {
        setSelectedScanId(raiseScanId)
        setManufacturerName('')
        setRuleId('')
        setMeasuredValue('')
        setRequiredValue('')
        setIsRaiseModalOpen(true)
        setRaiseFormError(null)
      } else {
        // UI Rule 1 Strict Refusal
        setRaiseFormError(
          eligibility.reason ||
            'Refusal: A complaint can only be raised from a verdict explicitly confirmed by an officer.',
        )
        setIsRaiseModalOpen(true)
      }
    }
  }, [searchParams, scans])

  // Metrics
  const metrics = useMemo(() => {
    let raised = 0
    let acknowledged = 0
    let resolved = 0
    let rejected = 0

    for (const thread of threads) {
      switch (thread.latest_record.status) {
        case 'raised':
          raised++
          break
        case 'acknowledged':
          acknowledged++
          break
        case 'resolved':
          resolved++
          break
        case 'rejected':
          rejected++
          break
      }
    }

    return { total: threads.length, raised, acknowledged, resolved, rejected }
  }, [threads])

  // Filtered threads
  const filteredThreads = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return threads.filter((thread) => {
      if (statusFilter !== 'ALL' && thread.latest_record.status !== statusFilter) {
        return false
      }
      if (q) {
        const matchesId = thread.latest_record.id.toLowerCase().includes(q)
        const matchesScan = thread.scan_id.toLowerCase().includes(q)
        const matchesMfr = thread.manufacturer_name.toLowerCase().includes(q)
        const matchesProd = thread.product_description.toLowerCase().includes(q)
        const matchesIssue = thread.latest_record.issue_summary.toLowerCase().includes(q)
        if (!matchesId && !matchesScan && !matchesMfr && !matchesProd && !matchesIssue) {
          return false
        }
      }
      return true
    })
  }, [threads, statusFilter, searchQuery])

  // Handle scan selection change in Raise modal
  const handleScanSelectChange = (scanId: string) => {
    setSelectedScanId(scanId)
    setRaiseFormError(null)
  }

  // Submit New Complaint (RAISED) via POST /complaints
  const handleRaiseSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Strict validation of UI Rule 1
    const check = checkCanRaiseComplaint(selectedScanId, scans)
    if (!check.allowed) {
      setRaiseFormError(
        'Statutory Refusal: A complaint can ONLY be raised from a verdict that an officer has explicitly confirmed. The UI strictly forbids complaints on raw machine verdicts.',
      )
      return
    }

    if (!manufacturerName.trim()) {
      setRaiseFormError('Declared manufacturer name is required.')
      return
    }
    if (!ruleId.trim()) {
      setRaiseFormError('Rule ID (clause reference) is required.')
      return
    }
    if (!measuredValue.trim()) {
      setRaiseFormError('Measured value is required.')
      return
    }
    if (!requiredValue.trim()) {
      setRaiseFormError('Required value is required.')
      return
    }

    setRaiseSubmitting(true)
    setRaiseFormError(null)
    try {
      const { data, error } = await apiClient.POST('/complaints', {
        body: {
          scan_id: selectedScanId,
          manufacturer_name: manufacturerName.trim(),
          rule_id: ruleId.trim(),
          field,
          measured_value: measuredValue.trim(),
          required_value: requiredValue.trim(),
        },
      })

      if (error || !data) {
        setRaiseFormError(
          'Server rejected the complaint. Ensure the scan is finalised with a confirmed POTENTIAL_VIOLATION verdict.',
        )
        return
      }

      // Prepend the new record to state (append-only)
      setRecords((prev) => [apiRecordToRecord(data), ...prev])
      setIsRaiseModalOpen(false)
      setSearchParams({})
      setSelectedScanId('')
      setManufacturerName('')
      setRuleId('')
      setMeasuredValue('')
      setRequiredValue('')
      setRaiseFormError(null)
    } catch {
      setRaiseFormError('Network error. Please try again.')
    } finally {
      setRaiseSubmitting(false)
    }
  }

  /**
   * Lifecycle transitions (acknowledge / resolve / reject) are append-only local state
   * operations until the backend exposes a transition endpoint. Officer identity is not
   * hard-coded — it is intentionally omitted from locally-constructed records and will
   * be filled server-side when the transition endpoint is available.
   */
  const handleTransitionSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!transitionTarget) return

    const { record, toStatus } = transitionTarget
    if (!actionNote.trim()) {
      return
    }

    const newRecord: ComplaintRecord = {
      id: `local-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      scan_id: record.scan_id,
      verdict_id: record.verdict_id,
      manufacturer_name: record.manufacturer_name,
      issue_summary: actionNote.trim(),
      status: toStatus,
      // Officer identity is sourced from the authenticated session server-side;
      // locally-created transition records carry an empty string until persisted.
      raised_by_officer_id: '',
      raised_at: new Date().toISOString(),
      supersedes_id: record.id,
    }

    setRecords((prev) => [newRecord, ...prev])
    setTransitionTarget(null)
    setActionNote('')
  }

  /**
   * Reopen: append a new RAISED record superseding the resolved/rejected one.
   * Same as transitions — no backend endpoint yet; officer identity is not hard-coded.
   */
  const handleReopenSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reopenTarget) return

    if (!reopenJustification.trim()) {
      setReopenError('A specific justification for reopening is required by audit rules.')
      return
    }

    const newRecord: ComplaintRecord = {
      id: `local-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      scan_id: reopenTarget.scan_id,
      verdict_id: reopenTarget.verdict_id,
      manufacturer_name: reopenTarget.manufacturer_name,
      issue_summary: reopenJustification.trim(),
      status: 'raised',
      raised_by_officer_id: '',
      raised_at: new Date().toISOString(),
      supersedes_id: reopenTarget.id,
    }

    setRecords((prev) => [newRecord, ...prev])
    setReopenTarget(null)
    setReopenJustification('')
    setReopenError(null)
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <OfficerHeader currentTitle="Complaints Ledger" />

      <main className="mx-auto max-w-[1280px] px-4 pb-16 pt-4">
        {/* Masthead */}
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-ink pb-4">
          <div>
            <h1 className="text-title">Complaint Raise &amp; Track Ledger</h1>
            <p className="mt-1 text-secondary text-mute">
              Statutory manufacturer escalation tracking under Legal Metrology Rules, 2011.
              Immutable append-only record: lifecycle progression and reopening append superseding events.
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              setSelectedScanId('')
              setManufacturerName('')
              setRuleId('')
              setMeasuredValue('')
              setRequiredValue('')
              setRaiseFormError(null)
              setIsRaiseModalOpen(true)
            }}
            className="flex min-h-target items-center border border-ink bg-ink px-4 py-2 text-label font-medium text-paper hover:bg-ink/90 active:bg-ink/80"
          >
            + Raise New Complaint
          </button>
        </div>

        {/* Lifecycle Metrics Bar */}
        <div className="mt-4 grid grid-cols-2 gap-3 border border-hairline bg-paper p-3 sm:grid-cols-5">
          <div className="border-r border-hairline/60 pr-2">
            <span className="block text-label text-mute">Total Escalations</span>
            <span className="font-mono text-title font-semibold">{metrics.total}</span>
          </div>
          <div className="border-r border-hairline/60 pr-2">
            <span className="block text-label text-mute">RAISED (Awaiting Ack)</span>
            <span className="font-mono text-title font-semibold text-query">
              {metrics.raised}
            </span>
          </div>
          <div className="border-r border-hairline/60 pr-2">
            <span className="block text-label text-mute">ACKNOWLEDGED</span>
            <span className="font-mono text-title font-semibold text-mute">
              {metrics.acknowledged}
            </span>
          </div>
          <div className="border-r border-hairline/60 pr-2">
            <span className="block text-label text-mute">RESOLVED</span>
            <span className="font-mono text-title font-semibold text-attest">
              {metrics.resolved}
            </span>
          </div>
          <div>
            <span className="block text-label text-mute">REJECTED</span>
            <span className="font-mono text-title font-semibold text-seal">
              {metrics.rejected}
            </span>
          </div>
        </div>

        {/* Filters & Search */}
        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-3 border-b border-hairline pb-4">
          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Search Complaints</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, manufacturer, or commodity..."
              className="min-h-target w-72 border border-ink bg-paper px-3 py-1.5 text-body placeholder:text-mute"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Lifecycle Status</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ComplaintStatus | 'ALL')}
              className="min-h-target border border-ink bg-paper px-3 py-1.5 text-body"
            >
              <option value="ALL">All Lifecycle Stages</option>
              <option value="raised">RAISED</option>
              <option value="acknowledged">ACKNOWLEDGED</option>
              <option value="resolved">RESOLVED</option>
              <option value="rejected">REJECTED</option>
            </select>
          </label>

          {(searchQuery || statusFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setStatusFilter('ALL')
              }}
              className="min-h-target border border-hairline px-3 py-1.5 text-label text-mute hover:border-ink hover:text-ink"
            >
              Clear filters
            </button>
          )}
        </section>

        {/* Complaints Table */}
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between text-label text-mute">
            <span className="font-mono">
              {filteredThreads.length} active threads recorded in append-only store
            </span>
            <span>Immutable event ledger (no edit-in-place)</span>
          </div>

          {loading ? (
            <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
              Loading complaints ledger…
            </div>
          ) : fetchError ? (
            <div
              role="alert"
              className="mt-6 border-2 border-seal bg-paper p-4 text-body text-seal"
            >
              {fetchError}
            </div>
          ) : filteredThreads.length === 0 ? (
            <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
              No complaint records found matching the criteria.
            </div>
          ) : (
            <div className="space-y-4">
              {filteredThreads.map((thread) => {
                const head = thread.latest_record
                const scan = scans.find((s) => s.id === thread.scan_id)

                return (
                  <article
                    key={thread.thread_id}
                    className="border-b-2 border-ink pb-5 pt-3 transition-colors hover:bg-focus-tint/20"
                  >
                    {/* Header line */}
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-body font-bold text-ink">
                            {head.id}
                          </span>
                          {head.supersedes_id && (
                            <span className="border border-hairline px-1.5 py-0.5 font-mono text-label text-mute">
                              Supersedes #{head.supersedes_id}
                            </span>
                          )}
                          <span className="font-mono text-label text-mute">
                            • Event {thread.history.length} in thread
                          </span>
                        </div>
                        <h2 className="mt-1 text-section font-semibold text-ink">
                          {thread.manufacturer_name}
                        </h2>
                        <p className="text-secondary text-mute">
                          Commodity: {thread.product_description}
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1.5">
                        {statusBadge(head.status)}
                        {scan?.verdict && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-label text-mute">Confirmed:</span>
                            <VerdictTag verdict={scan.verdict as Verdict} />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Issue Summary */}
                    <div className="mt-3 border-l-2 border-ink pl-3">
                      <span className="block text-label text-mute">
                        Statutory Contravention Statement:
                      </span>
                      <p className="text-body text-ink">{head.issue_summary}</p>
                    </div>

                    {/* Lifecycle Progress Visualizer */}
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-hairline/60 pt-2 font-mono text-label text-mute">
                      <span>Lifecycle:</span>
                      <span
                        className={
                          head.status === 'raised'
                            ? 'font-bold text-query underline'
                            : 'text-ink'
                        }
                      >
                        1. RAISED
                      </span>
                      <span>→</span>
                      <span
                        className={
                          head.status === 'acknowledged'
                            ? 'font-bold text-mute underline'
                            : head.status === 'resolved' || head.status === 'rejected'
                              ? 'text-ink'
                              : 'text-hairline'
                        }
                      >
                        2. ACKNOWLEDGED
                      </span>
                      <span>→</span>
                      <span
                        className={
                          head.status === 'resolved'
                            ? 'font-bold text-attest underline'
                            : head.status === 'rejected'
                              ? 'font-bold text-seal underline'
                              : 'text-hairline'
                        }
                      >
                        3. {head.status === 'rejected' ? 'REJECTED' : 'RESOLVED'}
                      </span>
                    </div>

                    {/* Metadata & Actions */}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-3">
                      <div className="font-mono text-label text-mute">
                        {head.raised_by_officer_id ? (
                          <span>Officer: {head.raised_by_officer_id}</span>
                        ) : (
                          <span>Officer: pending server sync</span>
                        )}
                        <span className="mx-2">•</span>
                        <span>{formatTimestamp(head.raised_at)}</span>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {/* Audit Trail Button */}
                        <button
                          type="button"
                          onClick={() => setActiveThread(thread)}
                          className="flex min-h-target items-center border border-ink bg-paper px-3 py-1 font-mono text-label text-ink hover:bg-mute/10"
                        >
                          Audit History ({thread.history.length})
                        </button>

                        {/* Lifecycle Progression Affordances (Append-only!) */}
                        {head.status === 'raised' && (
                          <button
                            type="button"
                            onClick={() =>
                              setTransitionTarget({
                                record: head,
                                toStatus: 'acknowledged',
                              })
                            }
                            className="flex min-h-target items-center border border-ink bg-ink px-3 py-1 text-label text-paper hover:bg-ink/90"
                          >
                            Record Acknowledgement →
                          </button>
                        )}

                        {head.status === 'acknowledged' && (
                          <>
                            <button
                              type="button"
                              onClick={() =>
                                setTransitionTarget({
                                  record: head,
                                  toStatus: 'resolved',
                                })
                              }
                              className="flex min-h-target items-center border border-attest bg-paper px-3 py-1 text-label font-medium text-attest hover:bg-attest/10"
                            >
                              Resolve Complaint ✓
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setTransitionTarget({
                                  record: head,
                                  toStatus: 'rejected',
                                })
                              }
                              className="flex min-h-target items-center border border-seal bg-paper px-3 py-1 text-label font-medium text-seal hover:bg-seal/10"
                            >
                              Reject Complaint ✕
                            </button>
                          </>
                        )}

                        {/* UI Rule 3: Reopen Complaint */}
                        {(head.status === 'resolved' || head.status === 'rejected') && (
                          <button
                            type="button"
                            onClick={() => {
                              setReopenTarget(head)
                              setReopenJustification('')
                              setReopenError(null)
                            }}
                            className="flex min-h-target items-center border border-ink bg-paper px-3 py-1 font-mono text-label text-ink hover:bg-mute/10"
                          >
                            Reopen Complaint ↺
                          </button>
                        )}
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </div>

        {/* Modal 1: Thread History (Append-Only Audit View) */}
        {activeThread && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-history-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          >
            <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto border-2 border-ink bg-paper p-5 sm:p-6">
              <div className="flex items-start justify-between border-b border-ink pb-3">
                <div>
                  <span className="font-mono text-label text-mute">
                    APPEND-ONLY AUDIT LEDGER • THREAD #{activeThread.thread_id}
                  </span>
                  <h2 id="audit-history-title" className="text-title">
                    {activeThread.manufacturer_name}
                  </h2>
                  <p className="font-mono text-label text-mute">
                    Inspection Scan: {activeThread.scan_id} • Verdict: {activeThread.verdict_id}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveThread(null)}
                  className="flex min-h-target items-center px-3 font-mono text-body hover:text-mute"
                >
                  ✕
                </button>
              </div>

              <div className="mt-4">
                <p className="text-secondary text-mute">
                  Legal metrology escalation threads are immutable. Every row represents an event
                  signed by an officer timestamp. Superseding records name their predecessor via
                  `supersedes_id` without in-place mutation.
                </p>

                <div className="mt-4 space-y-3">
                  {activeThread.history.map((rec, index) => (
                    <div
                      key={rec.id}
                      className="border border-hairline bg-paper p-3 text-secondary"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline/60 pb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-label font-bold text-ink">
                            Event #{index + 1}: {rec.id}
                          </span>
                          {statusBadge(rec.status)}
                        </div>
                        <span className="font-mono text-label text-mute">
                          {formatTimestamp(rec.raised_at)}
                        </span>
                      </div>

                      <div className="mt-2 space-y-1">
                        <p className="text-body font-medium text-ink">{rec.issue_summary}</p>
                        <p className="font-mono text-label text-mute">
                          {rec.raised_by_officer_id
                            ? `Officer: ${rec.raised_by_officer_id}`
                            : 'Officer: pending server sync'}
                          {rec.supersedes_id
                            ? ` • Supersedes #${rec.supersedes_id}`
                            : ' • Initial Root Event'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 flex justify-end border-t border-ink pt-4">
                <button
                  type="button"
                  onClick={() => setActiveThread(null)}
                  className="min-h-target border border-ink px-4 py-2 text-label text-ink hover:bg-mute/10"
                >
                  Close Audit Ledger
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 2: Raise New Complaint (UI Rule 1 Enforced!) */}
        {isRaiseModalOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="raise-complaint-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          >
            <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto border-2 border-ink bg-paper p-5 sm:p-6">
              <div className="flex items-start justify-between border-b border-ink pb-3">
                <div>
                  <span className="font-mono text-label font-bold text-ink">
                    STATUTORY ENFORCEMENT ESCALATION
                  </span>
                  <h2 id="raise-complaint-title" className="text-title">
                    Raise Manufacturer Complaint
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsRaiseModalOpen(false)
                    setSearchParams({})
                  }}
                  className="flex min-h-target items-center px-3 font-mono text-body hover:text-mute"
                >
                  ✕
                </button>
              </div>

              {/* UI Rule 1 Statutory Safeguard Notice */}
              <div className="mt-4 border-l-4 border-ink bg-paper p-3 text-secondary text-mute">
                <p className="font-semibold text-ink">
                  UI Rule 1 — Mandatory Human Confirmation:
                </p>
                <p className="mt-0.5 text-label">
                  Under the Legal Metrology (Packaged Commodities) Rules, 2011, a complaint can ONLY
                  be raised from a verdict that an officer has explicitly confirmed. The system
                  strictly forbids and excludes unconfirmed machine recommendations.
                </p>
              </div>

              {raiseFormError && (
                <div
                  role="alert"
                  className="mt-4 border-2 border-seal bg-paper p-3 text-secondary text-seal"
                >
                  <p className="font-semibold">{raiseFormError}</p>
                </div>
              )}

              <form onSubmit={(e) => { void handleRaiseSubmit(e) }} className="mt-4 space-y-4">
                {/* Scan selector: ONLY lists CONFIRMED scans */}
                <div>
                  <label htmlFor="select-scan" className="block text-label text-mute">
                    Select Confirmed Inspection Scan *
                  </label>
                  <select
                    id="select-scan"
                    value={selectedScanId}
                    onChange={(e) => handleScanSelectChange(e.target.value)}
                    required
                    className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 font-mono text-body text-ink"
                  >
                    <option value="">-- Choose an officer-confirmed scan --</option>
                    {confirmedEligibleSubmissions.map((sub) => (
                      <option key={sub.id} value={sub.id}>
                        {sub.id} — Confirmed {sub.verdict || 'REVIEW'} ({sub.product_category || 'Commodity'})
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 font-mono text-label text-mute">
                    * Showing {confirmedEligibleSubmissions.length} inspections with confirmed verdicts. Unconfirmed machine scans are omitted.
                  </p>
                </div>

                <div>
                  <label htmlFor="mfr-name" className="block text-label text-mute">
                    Declared Manufacturer Name *
                  </label>
                  <input
                    id="mfr-name"
                    type="text"
                    value={manufacturerName}
                    onChange={(e) => setManufacturerName(e.target.value)}
                    required
                    placeholder="e.g. Apex Agro Refining Private Limited"
                    className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                  />
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label htmlFor="rule-id" className="block text-label text-mute">
                      Rule ID / Clause Reference *
                    </label>
                    <input
                      id="rule-id"
                      type="text"
                      value={ruleId}
                      onChange={(e) => setRuleId(e.target.value)}
                      required
                      placeholder="e.g. rule-6-1-d"
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 font-mono text-body text-ink"
                    />
                  </div>
                  <div>
                    <label htmlFor="field-select" className="block text-label text-mute">
                      Declaration Field *
                    </label>
                    <select
                      id="field-select"
                      value={field}
                      onChange={(e) => setField(e.target.value as DeclarationField)}
                      required
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 font-mono text-body text-ink"
                    >
                      {DECLARATION_FIELDS.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label htmlFor="measured-value" className="block text-label text-mute">
                      Measured Value (observed) *
                    </label>
                    <input
                      id="measured-value"
                      type="text"
                      value={measuredValue}
                      onChange={(e) => setMeasuredValue(e.target.value)}
                      required
                      placeholder="e.g. 480g"
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                    />
                  </div>
                  <div>
                    <label htmlFor="required-value" className="block text-label text-mute">
                      Required Value (declared) *
                    </label>
                    <input
                      id="required-value"
                      type="text"
                      value={requiredValue}
                      onChange={(e) => setRequiredValue(e.target.value)}
                      required
                      placeholder="e.g. 500g"
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 border-t border-ink pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setIsRaiseModalOpen(false)
                      setSearchParams({})
                    }}
                    className="min-h-target px-4 py-2 text-label text-mute hover:text-ink"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!selectedScanId || raiseSubmitting}
                    className={`min-h-target border px-6 py-2 text-label font-medium ${
                      selectedScanId && !raiseSubmitting
                        ? 'border-ink bg-ink text-paper hover:bg-ink/90'
                        : 'cursor-not-allowed border-hairline bg-hairline text-mute'
                    }`}
                  >
                    {raiseSubmitting ? 'Submitting…' : 'Submit Formal Complaint'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 3: Lifecycle Transition (Append-only event creation) */}
        {transitionTarget && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="transition-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          >
            <div className="w-full max-w-lg border-2 border-ink bg-paper p-5 sm:p-6">
              <div className="flex items-start justify-between border-b border-ink pb-3">
                <div>
                  <span className="font-mono text-label text-mute">
                    APPEND-ONLY LIFECYCLE PROGRESSION
                  </span>
                  <h2 id="transition-title" className="text-section font-semibold">
                    Record {statusLabel(transitionTarget.toStatus)}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => setTransitionTarget(null)}
                  className="flex min-h-target items-center px-3 font-mono text-body hover:text-mute"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleTransitionSubmit} className="mt-4 space-y-3">
                <p className="text-secondary text-mute">
                  Recording this transition writes a new immutable event row superseding{' '}
                  <span className="font-mono font-bold text-ink">
                    #{transitionTarget.record.id}
                  </span>
                  .
                </p>

                <div>
                  <label htmlFor="action-note" className="block text-label text-mute">
                    {transitionTarget.toStatus === 'acknowledged'
                      ? 'Manufacturer Acknowledgement Reference & Details *'
                      : transitionTarget.toStatus === 'resolved'
                        ? 'Resolution Summary & Corrective Undertaking *'
                        : 'Rejection Grounds & Verification Findings *'}
                  </label>
                  <textarea
                    id="action-note"
                    rows={3}
                    value={actionNote}
                    onChange={(e) => setActionNote(e.target.value)}
                    required
                    placeholder={
                      transitionTarget.toStatus === 'acknowledged'
                        ? 'Enter manufacturer notice reference and date of receipt...'
                        : transitionTarget.toStatus === 'resolved'
                          ? 'Detail the manufacturer undertaking, revised packaging artwork, or batch withdrawal...'
                          : 'State why the escalation was dismissed or certificate under which exemption was granted...'
                    }
                    className="mt-1 w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 border-t border-ink pt-3">
                  <button
                    type="button"
                    onClick={() => setTransitionTarget(null)}
                    className="min-h-target px-4 py-2 text-label text-mute hover:text-ink"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!actionNote.trim()}
                    className="min-h-target border border-ink bg-ink px-4 py-2 text-label font-medium text-paper hover:bg-ink/90 disabled:cursor-not-allowed disabled:bg-hairline"
                  >
                    Append {statusLabel(transitionTarget.toStatus)} Record
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal 4: Reopen Complaint (UI Rule 3: Append-only superseding event) */}
        {reopenTarget && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reopen-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          >
            <div className="w-full max-w-lg border-2 border-ink bg-paper p-5 sm:p-6">
              <div className="flex items-start justify-between border-b border-ink pb-3">
                <div>
                  <span className="font-mono text-label text-mute">
                    UI RULE 3 — APPEND-ONLY ARCHITECTURE
                  </span>
                  <h2 id="reopen-title" className="text-section font-semibold">
                    Reopen Complaint #{reopenTarget.id}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => setReopenTarget(null)}
                  className="flex min-h-target items-center px-3 font-mono text-body hover:text-mute"
                >
                  ✕
                </button>
              </div>

              <div className="mt-3 border border-hairline bg-paper p-3 text-secondary text-mute">
                <p className="text-body font-medium text-ink">
                  {reopenTarget.manufacturer_name}
                </p>
                <p className="font-mono text-label">
                  Previous status: {statusLabel(reopenTarget.status)} • Supersedes #{reopenTarget.id}
                </p>
                <p className="mt-1 text-label">
                  Reopening does not modify the existing record in place. It appends a new
                  superseding event in RAISED status to the audit trail.
                </p>
              </div>

              {reopenError && (
                <p className="mt-2 text-label text-seal">{reopenError}</p>
              )}

              <form onSubmit={handleReopenSubmit} className="mt-4 space-y-3">
                <div>
                  <label htmlFor="reopen-justification" className="block text-label text-mute">
                    Reopening Justification / New Investigation Evidence *
                  </label>
                  <textarea
                    id="reopen-justification"
                    rows={3}
                    value={reopenJustification}
                    onChange={(e) => setReopenJustification(e.target.value)}
                    required
                    placeholder="Detail subsequent inspection findings or persistence of package shortfall..."
                    className="mt-1 w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 border-t border-ink pt-3">
                  <button
                    type="button"
                    onClick={() => setReopenTarget(null)}
                    className="min-h-target px-4 py-2 text-label text-mute hover:text-ink"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!reopenJustification.trim()}
                    className="min-h-target border border-ink bg-ink px-4 py-2 text-label font-medium text-paper hover:bg-ink/90 disabled:cursor-not-allowed disabled:bg-hairline"
                  >
                    Append Reopened Complaint (RAISED)
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
