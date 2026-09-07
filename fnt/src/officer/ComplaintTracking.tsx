import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  type ComplaintRecord,
  type ComplaintStatus,
  type ComplaintThread,
  buildComplaintThreads,
  checkCanRaiseComplaint,
  loadComplaintRecords,
  saveComplaintRecords,
} from '../fixtures/complaints.fixture'
import { VENDOR_SUBMISSIONS } from '../fixtures/vendor-submissions.fixture'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictTag } from './components/VerdictBanner'

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

function statusBadge(status: ComplaintStatus) {
  switch (status) {
    case 'RAISED':
      return (
        <span className="inline-flex items-center border border-dashed border-query bg-paper px-2 py-0.5 font-mono text-label font-medium text-query">
          RAISED
        </span>
      )
    case 'ACKNOWLEDGED':
      return (
        <span className="inline-flex items-center border border-solid border-mute bg-paper px-2 py-0.5 font-mono text-label font-medium text-mute">
          ACKNOWLEDGED
        </span>
      )
    case 'RESOLVED':
      return (
        <span className="inline-flex items-center border border-solid border-attest bg-paper px-2 py-0.5 font-mono text-label font-medium text-attest">
          ✓ RESOLVED
        </span>
      )
    case 'REJECTED':
      return (
        <span className="inline-flex items-center border border-solid border-seal bg-paper px-2 py-0.5 font-mono text-label font-medium text-seal">
          ✕ REJECTED
        </span>
      )
  }
}

export function ComplaintTracking() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [records, setRecords] = useState<ComplaintRecord[]>(() => loadComplaintRecords())
  const [statusFilter, setStatusFilter] = useState<ComplaintStatus | 'ALL'>('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  // Modals & Flows
  const [activeThread, setActiveThread] = useState<ComplaintThread | null>(null)
  const [isRaiseModalOpen, setIsRaiseModalOpen] = useState(false)
  const [reopenTarget, setReopenTarget] = useState<ComplaintRecord | null>(null)
  const [transitionTarget, setTransitionTarget] = useState<{
    record: ComplaintRecord
    toStatus: 'ACKNOWLEDGED' | 'RESOLVED' | 'REJECTED'
  } | null>(null)

  // Raise Form State
  const [selectedScanId, setSelectedScanId] = useState<string>('')
  const [manufacturerName, setManufacturerName] = useState<string>('')
  const [issueSummary, setIssueSummary] = useState<string>('')
  const [officerId, setOfficerId] = useState<string>('KLM-HYD-04')
  const [officerName, setOfficerName] = useState<string>('R. K. Sharma')
  const [eventNote, setEventNote] = useState<string>('')
  const [raiseFormError, setRaiseFormError] = useState<string | null>(null)

  // Transition & Reopen form inputs
  const [actionNote, setActionNote] = useState<string>('')
  const [reopenJustification, setReopenJustification] = useState<string>('')
  const [reopenError, setReopenError] = useState<string | null>(null)

  // Persist records whenever they change
  const updateRecords = (newRecords: ComplaintRecord[]) => {
    setRecords(newRecords)
    saveComplaintRecords(newRecords)
  }

  // Derive threads from append-only records
  const threads = useMemo(() => buildComplaintThreads(records), [records])

  // Only CONFIRMED scans can have complaints raised against them (UI Rule 1)
  const confirmedEligibleSubmissions = useMemo(() => {
    return VENDOR_SUBMISSIONS.filter((s) => s.officer_confirmation.is_confirmed)
  }, [])

  // Handle raise_scan_id query param
  useEffect(() => {
    const raiseScanId = searchParams.get('raise_scan_id')
    if (raiseScanId) {
      const eligibility = checkCanRaiseComplaint(raiseScanId)
      if (eligibility.allowed && eligibility.submission) {
        setSelectedScanId(raiseScanId)
        setManufacturerName(eligibility.submission.manufacturer_name)
        setIssueSummary(eligibility.submission.issue_summary)
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
  }, [searchParams])

  // Metrics
  const metrics = useMemo(() => {
    let raised = 0
    let acknowledged = 0
    let resolved = 0
    let rejected = 0

    for (const thread of threads) {
      switch (thread.latest_record.status) {
        case 'RAISED':
          raised++
          break
        case 'ACKNOWLEDGED':
          acknowledged++
          break
        case 'RESOLVED':
          resolved++
          break
        case 'REJECTED':
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
    const sub = confirmedEligibleSubmissions.find((s) => s.scan_id === scanId)
    if (sub) {
      setManufacturerName(sub.manufacturer_name)
      setIssueSummary(sub.issue_summary)
    }
  }

  // Submit New Complaint (RAISED)
  const handleRaiseSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Strict validation of UI Rule 1
    const check = checkCanRaiseComplaint(selectedScanId)
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
    if (!issueSummary.trim()) {
      setRaiseFormError('Issue summary describing the contravention is required.')
      return
    }

    const sub = check.submission!
    const newRecord: ComplaintRecord = {
      id: `cmp-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      scan_id: sub.scan_id,
      verdict_id: sub.verdict_id,
      manufacturer_name: manufacturerName.trim(),
      issue_summary: issueSummary.trim(),
      status: 'RAISED',
      raised_by_officer_id: officerId.trim(),
      raised_by_officer_name: officerName.trim(),
      raised_at: new Date().toISOString(),
      supersedes_id: null,
      event_note: eventNote.trim() || 'Initial statutory complaint notice raised.',
    }

    updateRecords([newRecord, ...records])
    setIsRaiseModalOpen(false)
    setSearchParams({})
    setSelectedScanId('')
    setManufacturerName('')
    setIssueSummary('')
    setEventNote('')
    setRaiseFormError(null)
  }

  // Transition Lifecycle (Append-only record creation!)
  const handleTransitionSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!transitionTarget) return

    const { record, toStatus } = transitionTarget
    if (!actionNote.trim()) {
      return
    }

    const newRecord: ComplaintRecord = {
      id: `cmp-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      scan_id: record.scan_id,
      verdict_id: record.verdict_id,
      manufacturer_name: record.manufacturer_name,
      issue_summary: record.issue_summary,
      status: toStatus,
      raised_by_officer_id: 'KLM-HYD-04',
      raised_by_officer_name: 'R. K. Sharma',
      raised_at: new Date().toISOString(),
      supersedes_id: record.id,
      event_note: actionNote.trim(),
    }

    updateRecords([newRecord, ...records])
    setTransitionTarget(null)
    setActionNote('')
  }

  // UI Rule 3 (Append-Only): Reopen Complaint
  // Reopening a complaint is modeled as raising a new complaint record with status = 'RAISED'
  // that supersedes the resolved/rejected record!
  const handleReopenSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reopenTarget) return

    if (!reopenJustification.trim()) {
      setReopenError('A specific justification for reopening is required by audit rules.')
      return
    }

    const newRecord: ComplaintRecord = {
      id: `cmp-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 5)}`,
      scan_id: reopenTarget.scan_id,
      verdict_id: reopenTarget.verdict_id,
      manufacturer_name: reopenTarget.manufacturer_name,
      issue_summary: reopenJustification.trim(),
      status: 'RAISED',
      raised_by_officer_id: 'KLM-HYD-04',
      raised_by_officer_name: 'R. K. Sharma',
      raised_at: new Date().toISOString(),
      supersedes_id: reopenTarget.id,
      event_note: `Reopened escalation superseding #${reopenTarget.id}: ${reopenJustification.trim()}`,
    }

    updateRecords([newRecord, ...records])
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
            <h1 className="text-title">Complaint Raise & Track Ledger</h1>
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
              setIssueSummary('')
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
              <option value="RAISED">RAISED</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="REJECTED">REJECTED</option>
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

          {filteredThreads.length === 0 ? (
            <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
              No complaint records found matching the criteria.
            </div>
          ) : (
            <div className="space-y-4">
              {filteredThreads.map((thread) => {
                const head = thread.latest_record
                const submission = VENDOR_SUBMISSIONS.find((s) => s.scan_id === thread.scan_id)

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
                          Commodity: {thread.product_description} • Retail Premise: {thread.vendor_name} ({thread.district}, {thread.state})
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1.5">
                        {statusBadge(head.status)}
                        {submission && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-label text-mute">Confirmed:</span>
                            <VerdictTag verdict={submission.recommended_verdict} />
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
                      {head.event_note && (
                        <p className="mt-1 font-mono text-label text-mute">
                          Latest Note: {head.event_note}
                        </p>
                      )}
                    </div>

                    {/* Lifecycle Progress Visualizer */}
                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-hairline/60 pt-2 font-mono text-label text-mute">
                      <span>Lifecycle:</span>
                      <span
                        className={
                          head.status === 'RAISED'
                            ? 'font-bold text-query underline'
                            : 'text-ink'
                        }
                      >
                        1. RAISED
                      </span>
                      <span>→</span>
                      <span
                        className={
                          head.status === 'ACKNOWLEDGED'
                            ? 'font-bold text-mute underline'
                            : head.status === 'RESOLVED' || head.status === 'REJECTED'
                              ? 'text-ink'
                              : 'text-hairline'
                        }
                      >
                        2. ACKNOWLEDGED
                      </span>
                      <span>→</span>
                      <span
                        className={
                          head.status === 'RESOLVED'
                            ? 'font-bold text-attest underline'
                            : head.status === 'REJECTED'
                              ? 'font-bold text-seal underline'
                              : 'text-hairline'
                        }
                      >
                        3. {head.status === 'REJECTED' ? 'REJECTED' : 'RESOLVED'}
                      </span>
                    </div>

                    {/* Metadata & Actions */}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-3">
                      <div className="font-mono text-label text-mute">
                        <span>Recorded by {head.raised_by_officer_name} ({head.raised_by_officer_id})</span>
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
                        {head.status === 'RAISED' && (
                          <button
                            type="button"
                            onClick={() =>
                              setTransitionTarget({
                                record: head,
                                toStatus: 'ACKNOWLEDGED',
                              })
                            }
                            className="flex min-h-target items-center border border-ink bg-ink px-3 py-1 text-label text-paper hover:bg-ink/90"
                          >
                            Record Acknowledgement →
                          </button>
                        )}

                        {head.status === 'ACKNOWLEDGED' && (
                          <>
                            <button
                              type="button"
                              onClick={() =>
                                setTransitionTarget({
                                  record: head,
                                  toStatus: 'RESOLVED',
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
                                  toStatus: 'REJECTED',
                                })
                              }
                              className="flex min-h-target items-center border border-seal bg-paper px-3 py-1 text-label font-medium text-seal hover:bg-seal/10"
                            >
                              Reject Complaint ✕
                            </button>
                          </>
                        )}

                        {/* UI Rule 3: Reopen Complaint */}
                        {(head.status === 'RESOLVED' || head.status === 'REJECTED') && (
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
                        {rec.event_note && (
                          <p className="font-mono text-label text-mute">
                            Note: {rec.event_note}
                          </p>
                        )}
                        <p className="font-mono text-label text-mute">
                          Officer: {rec.raised_by_officer_name} ({rec.raised_by_officer_id})
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

              <form onSubmit={handleRaiseSubmit} className="mt-4 space-y-4">
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
                      <option key={sub.scan_id} value={sub.scan_id}>
                        {sub.scan_id} — {sub.product_description} (Confirmed {sub.recommended_verdict} by{' '}
                        {sub.officer_confirmation.officer_id})
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

                <div>
                  <label htmlFor="issue-summary" className="block text-label text-mute">
                    Contravention / Issue Summary *
                  </label>
                  <textarea
                    id="issue-summary"
                    rows={3}
                    value={issueSummary}
                    onChange={(e) => setIssueSummary(e.target.value)}
                    required
                    placeholder="State the observed contravention and applicable statutory rule clause..."
                    className="mt-1 w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                  />
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label htmlFor="officer-id" className="block text-label text-mute">
                      Reporting Officer ID
                    </label>
                    <input
                      id="officer-id"
                      type="text"
                      value={officerId}
                      onChange={(e) => setOfficerId(e.target.value)}
                      required
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 font-mono text-body text-ink"
                    />
                  </div>
                  <div>
                    <label htmlFor="officer-name" className="block text-label text-mute">
                      Officer Name
                    </label>
                    <input
                      id="officer-name"
                      type="text"
                      value={officerName}
                      onChange={(e) => setOfficerName(e.target.value)}
                      required
                      className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="event-note" className="block text-label text-mute">
                    Statutory Notice / Dispatch Reference
                  </label>
                  <input
                    id="event-note"
                    type="text"
                    value={eventNote}
                    onChange={(e) => setEventNote(e.target.value)}
                    placeholder="e.g. Notice issued under Rule 6(1)(a) ref LMO/2026/089"
                    className="mt-1 min-h-target w-full border border-ink bg-paper px-3 py-2 text-body text-ink"
                  />
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
                    disabled={!selectedScanId}
                    className={`min-h-target border px-6 py-2 text-label font-medium ${
                      selectedScanId
                        ? 'border-ink bg-ink text-paper hover:bg-ink/90'
                        : 'cursor-not-allowed border-hairline bg-hairline text-mute'
                    }`}
                  >
                    Submit Formal Complaint
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
                    Record {transitionTarget.toStatus}
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
                    {transitionTarget.toStatus === 'ACKNOWLEDGED'
                      ? 'Manufacturer Acknowledgement Reference & Details *'
                      : transitionTarget.toStatus === 'RESOLVED'
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
                      transitionTarget.toStatus === 'ACKNOWLEDGED'
                        ? 'Enter manufacturer notice reference and date of receipt...'
                        : transitionTarget.toStatus === 'RESOLVED'
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
                    Append {transitionTarget.toStatus} Record
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
                  Previous status: {reopenTarget.status} • Supersedes #{reopenTarget.id}
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
