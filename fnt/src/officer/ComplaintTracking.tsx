import { AnimatePresence, motion } from 'framer-motion'
import React, { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { CountUp } from '../ui/CountUp'
import { rise, spring, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictTag, verdictLabel } from './components/VerdictBanner'

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
      return 'Raised'
    case 'acknowledged':
      return 'Acknowledged'
    case 'resolved':
      return 'Resolved'
    case 'rejected':
      return 'Rejected'
  }
}

// A complaint status is a workflow position, not a finding about a package, so it
// never borrows a state colour. The four are told apart by border and fill alone.
const STATUS_PILL: Record<ComplaintStatus, string> = {
  raised: 'border-dashed border-ink bg-surface text-ink',
  acknowledged: 'border-hairline bg-surface text-mute',
  resolved: 'border-ink bg-ink text-paper',
  rejected: 'border-mute bg-sunken text-ink',
}

function statusBadge(status: ComplaintStatus) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-1 text-label font-medium ${STATUS_PILL[status]}`}
    >
      {statusLabel(status)}
    </span>
  )
}

const STATUS_FILTERS: ReadonlyArray<{ value: ComplaintStatus | 'ALL'; label: string }> = [
  { value: 'ALL', label: 'All' },
  { value: 'raised', label: 'Raised' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'rejected', label: 'Rejected' },
]

/** Where a thread sits on the raised, acknowledged, closed path. */
function LifecycleSteps({ status }: { status: ComplaintStatus }) {
  const closed = status === 'resolved' || status === 'rejected'
  const position = status === 'raised' ? 0 : status === 'acknowledged' ? 1 : 2
  const steps = ['Raised', 'Acknowledged', closed ? statusLabel(status) : 'Resolved']

  return (
    <ol aria-label="Lifecycle" className="flex flex-wrap items-center gap-1.5 text-label">
      {steps.map((step, index) => (
        <li key={step} className="flex items-center gap-1.5">
          {index > 0 && <span aria-hidden="true" className="h-px w-3 bg-hairline" />}
          <span
            aria-current={index === position ? 'step' : undefined}
            className={`rounded-full px-2.5 py-1 font-medium ${
              index === position
                ? 'bg-ink text-paper'
                : index < position
                  ? 'bg-ink/[0.07] text-ink'
                  : 'border border-dashed border-hairline text-mute'
            }`}
          >
            {step}
          </span>
        </li>
      ))}
    </ol>
  )
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Close"
      className="btn btn-ghost -mr-2 -mt-2 w-12 shrink-0 rounded-full px-0"
    >
      <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
        <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </button>
  )
}

/** A bottom sheet on a phone, a centred card from sm up. Rendered inside AnimatePresence. */
function Sheet({
  labelledBy,
  onClose,
  width,
  children,
}: {
  labelledBy: string
  onClose: () => void
  width: string
  children: React.ReactNode
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-end justify-center bg-[rgb(var(--c-shadow)/0.5)] sm:items-center sm:p-4"
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 48 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 48 }}
        transition={spring.glide}
        className={`max-h-[90vh] w-full overflow-y-auto rounded-t-sheet border border-hairline/70 bg-surface p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-e3 sm:rounded-card sm:p-6 ${width}`}
      >
        <span aria-hidden="true" className="mx-auto mb-4 block h-1 w-10 rounded-full bg-hairline sm:hidden" />
        {children}
      </motion.div>
    </motion.div>
  )
}

/** Three placeholders in the box of a thread card, so the list does not jump in. */
function ThreadSkeletons() {
  return (
    <div aria-busy="true" aria-label="Loading complaints" className="space-y-4 sm:space-y-6">
      {[0, 1, 2].map((i) => (
        <div key={i} className="card p-5 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2.5">
              <div className="skeleton h-4 w-40" />
              <div className="skeleton h-6 w-3/5" />
              <div className="skeleton h-4 w-2/5" />
            </div>
            <div className="skeleton h-7 w-24 rounded-full" />
          </div>
          <div className="skeleton mt-4 h-[72px] w-full rounded-ctl" />
          <div className="skeleton mt-4 h-7 w-64 max-w-full rounded-full" />
          <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
            <div className="skeleton h-12 w-full rounded-ctl sm:w-40" />
            <div className="skeleton h-12 w-full rounded-ctl sm:w-52" />
          </div>
        </div>
      ))}
    </div>
  )
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
  const [reloadKey, setReloadKey] = useState(0)

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
  }, [reloadKey])

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

  const closeRaise = () => {
    setIsRaiseModalOpen(false)
    setSearchParams({})
  }

  const metricTiles: ReadonlyArray<{ label: string; value: number }> = [
    { label: 'Total escalations', value: metrics.total },
    { label: 'Raised, awaiting acknowledgement', value: metrics.raised },
    { label: 'Acknowledged', value: metrics.acknowledged },
    { label: 'Resolved', value: metrics.resolved },
    { label: 'Rejected', value: metrics.rejected },
  ]

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="Complaints" />

      <main className="mx-auto max-w-[1280px] px-4 pb-28 pt-6 md:pb-16">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-3xl">
            <h1 className="text-title">Complaints</h1>
            <p className="mt-1.5 text-secondary text-mute">
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
            className="btn btn-primary w-full shrink-0 sm:w-auto"
          >
            <svg viewBox="0 0 16 16" aria-hidden="true" className="h-3.5 w-3.5" fill="none">
              <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Raise new complaint
          </button>
        </div>

        <motion.dl
          variants={stagger}
          initial="hidden"
          animate="shown"
          className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4"
        >
          {metricTiles.map((tile, index) => (
            <motion.div
              key={tile.label}
              variants={rise}
              className={`card flex flex-col justify-between gap-2 p-4 sm:p-5 ${index === 0 ? 'col-span-2 sm:col-span-1' : ''}`}
            >
              <dt className="text-label text-mute">{tile.label}</dt>
              <dd className="font-display text-display text-ink">
                {loading ? (
                  <span className="skeleton block h-[1.05em] w-14" />
                ) : fetchError ? (
                  // A count of zero would be a claim; the list did not load.
                  <span className="text-mute" aria-label="Not loaded">–</span>
                ) : (
                  <CountUp value={tile.value} />
                )}
              </dd>
            </motion.div>
          ))}
        </motion.dl>

        <section aria-label="Filters" className="mt-8 flex flex-col gap-4 lg:flex-row lg:items-end">
          <label className="flex flex-col gap-1.5 lg:w-96">
            <span className="text-label text-mute">Search complaints</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, manufacturer, or commodity..."
              className="input"
            />
          </label>

          <div className="flex min-w-0 flex-col gap-1.5">
            <span id="status-filter-label" className="text-label text-mute">
              Lifecycle status
            </span>
            <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
              <div
                role="group"
                aria-labelledby="status-filter-label"
                className="isolate inline-flex rounded-full border border-hairline/70 bg-sunken/70 p-1"
              >
                {STATUS_FILTERS.map((option) => {
                  const selected = statusFilter === option.value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setStatusFilter(option.value)}
                      className={`relative min-h-target whitespace-nowrap rounded-full px-4 text-secondary transition-colors duration-base ease-out ${
                        selected ? 'font-medium text-ink' : 'text-mute hover:text-ink'
                      }`}
                    >
                      {selected && (
                        <motion.span
                          layoutId="complaint-status-pill"
                          transition={spring.snap}
                          className="absolute inset-0 -z-10 rounded-full bg-surface shadow-e1"
                        />
                      )}
                      {option.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {(searchQuery || statusFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setStatusFilter('ALL')
              }}
              className="btn btn-ghost self-start lg:self-auto"
            >
              Clear filters
            </button>
          )}
        </section>

        <div className="mt-6">
          {loading ? (
            <ThreadSkeletons />
          ) : fetchError ? (
            <Notice
              role="alert"
              title={fetchError}
              action={
                <button
                  type="button"
                  onClick={() => setReloadKey((k) => k + 1)}
                  className="btn btn-quiet"
                >
                  Try again
                </button>
              }
            />
          ) : filteredThreads.length === 0 ? (
            <Notice title="No complaint records found matching the criteria." />
          ) : (
            <>
              <p className="mb-3 text-label text-mute">
                {filteredThreads.length} active threads recorded in append-only store. Immutable
                event ledger (no edit-in-place).
              </p>
              <motion.div
                key={statusFilter}
                variants={stagger}
                initial="hidden"
                animate="shown"
                className="space-y-4 sm:space-y-6"
              >
                {filteredThreads.map((thread) => {
                  const head = thread.latest_record
                  const scan = scans.find((s) => s.id === thread.scan_id)

                  return (
                    <motion.article key={thread.thread_id} variants={rise} className="card p-5 sm:p-6">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-label text-mute">
                            <span className="font-medium text-ink [overflow-wrap:anywhere]">{head.id}</span>
                            <span>Event {thread.history.length} in thread</span>
                            {/* Transitions are held in this page's state only; say so rather than let the row read as filed. */}
                            {head.id.startsWith('local-') && (
                              <span className="rounded-full border border-dotted border-mute px-2 py-0.5 font-sans">
                                This session only
                              </span>
                            )}
                          </div>
                          <h2 className="mt-1.5 font-sans text-section text-ink [overflow-wrap:anywhere]">
                            {thread.manufacturer_name}
                          </h2>
                          <p className="text-secondary text-mute">
                            Commodity: {thread.product_description}
                          </p>
                          {head.supersedes_id && (
                            <p className="mt-1 font-mono text-label text-mute [overflow-wrap:anywhere]">
                              Supersedes #{head.supersedes_id}
                            </p>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-2 sm:flex-col sm:items-end">
                          {statusBadge(head.status)}
                          {scan?.verdict && (
                            <div className="flex items-center gap-1.5">
                              <span className="text-label text-mute">Confirmed:</span>
                              <VerdictTag verdict={scan.verdict as Verdict} />
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-4 rounded-ctl bg-sunken/60 p-3.5">
                        <span className="block text-label text-mute">
                          Statutory contravention statement
                        </span>
                        <p className="mt-0.5 text-body text-ink [overflow-wrap:anywhere]">
                          {head.issue_summary}
                        </p>
                      </div>

                      <div className="mt-4">
                        <LifecycleSteps status={head.status} />
                      </div>

                      <div className="mt-5 flex flex-col gap-3 border-t border-hairline/70 pt-4 lg:flex-row lg:items-center lg:justify-between">
                        <p className="font-mono text-label text-mute">
                          {head.raised_by_officer_id ? (
                            <span>Officer: {head.raised_by_officer_id}</span>
                          ) : (
                            <span>Officer: pending server sync</span>
                          )}
                          <span className="mx-2" aria-hidden="true">·</span>
                          <span>{formatTimestamp(head.raised_at)}</span>
                        </p>

                        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
                          <button
                            type="button"
                            onClick={() => setActiveThread(thread)}
                            className="btn btn-quiet"
                          >
                            Audit history ({thread.history.length})
                          </button>

                          {head.status === 'raised' && (
                            <button
                              type="button"
                              onClick={() =>
                                setTransitionTarget({
                                  record: head,
                                  toStatus: 'acknowledged',
                                })
                              }
                              className="btn btn-primary"
                            >
                              Record acknowledgement
                            </button>
                          )}

                          {head.status === 'acknowledged' && (
                            <>
                              <button
                                type="button"
                                onClick={() =>
                                  setTransitionTarget({
                                    record: head,
                                    toStatus: 'rejected',
                                  })
                                }
                                className="btn btn-quiet"
                              >
                                Reject complaint
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  setTransitionTarget({
                                    record: head,
                                    toStatus: 'resolved',
                                  })
                                }
                                className="btn btn-primary"
                              >
                                Resolve complaint
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
                              className="btn btn-quiet"
                            >
                              Reopen complaint
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.article>
                  )
                })}
              </motion.div>
            </>
          )}
        </div>
      </main>

      <AnimatePresence>
        {/* Thread history (append-only audit view) */}
        {activeThread && (
          <Sheet
            key="audit"
            labelledBy="audit-history-title"
            onClose={() => setActiveThread(null)}
            width="sm:max-w-3xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 id="audit-history-title" className="text-title [overflow-wrap:anywhere]">
                  {activeThread.manufacturer_name}
                </h2>
                <p className="mt-1 font-mono text-label text-mute [overflow-wrap:anywhere]">
                  Append-only audit ledger · Thread #{activeThread.thread_id}
                </p>
                <p className="font-mono text-label text-mute [overflow-wrap:anywhere]">
                  Inspection scan: {activeThread.scan_id} · Verdict: {activeThread.verdict_id}
                </p>
              </div>
              <CloseButton onClick={() => setActiveThread(null)} />
            </div>

            <p className="mt-4 text-secondary text-mute">
              Legal metrology escalation threads are immutable. Every row represents an event
              signed by an officer timestamp. Superseding records name their predecessor via
              `supersedes_id` without in-place mutation.
            </p>

            <motion.ol variants={stagger} initial="hidden" animate="shown" className="mt-4 space-y-3">
              {activeThread.history.map((rec, index) => (
                <motion.li
                  key={rec.id}
                  variants={rise}
                  className="rounded-ctl border border-hairline/70 bg-sunken/50 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <span className="font-mono text-label font-medium text-ink [overflow-wrap:anywhere]">
                        Event #{index + 1}: {rec.id}
                      </span>
                      {statusBadge(rec.status)}
                    </div>
                    <span className="font-mono text-label text-mute">
                      {formatTimestamp(rec.raised_at)}
                    </span>
                  </div>

                  <p className="mt-2 text-body text-ink [overflow-wrap:anywhere]">{rec.issue_summary}</p>
                  <p className="mt-1 font-mono text-label text-mute [overflow-wrap:anywhere]">
                    {rec.raised_by_officer_id
                      ? `Officer: ${rec.raised_by_officer_id}`
                      : 'Officer: pending server sync'}
                    {rec.supersedes_id
                      ? ` · Supersedes #${rec.supersedes_id}`
                      : ' · Initial root event'}
                  </p>
                </motion.li>
              ))}
            </motion.ol>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveThread(null)}
                className="btn btn-quiet w-full sm:w-auto"
              >
                Close audit ledger
              </button>
            </div>
          </Sheet>
        )}

        {/* Raise new complaint (UI Rule 1 enforced) */}
        {isRaiseModalOpen && (
          <Sheet key="raise" labelledBy="raise-complaint-title" onClose={closeRaise} width="sm:max-w-2xl">
            <div className="flex items-start justify-between gap-3">
              <h2 id="raise-complaint-title" className="text-title">
                Raise manufacturer complaint
              </h2>
              <CloseButton onClick={closeRaise} />
            </div>

            {/* UI Rule 1 statutory safeguard notice */}
            <div className="mt-4 rounded-ctl bg-sunken/60 p-4 text-secondary text-mute">
              <p className="font-semibold text-ink">UI Rule 1 — Mandatory human confirmation</p>
              <p className="mt-1">
                Under the Legal Metrology (Packaged Commodities) Rules, 2011, a complaint can ONLY
                be raised from a verdict that an officer has explicitly confirmed. The system
                strictly forbids and excludes unconfirmed machine recommendations.
              </p>
            </div>

            {raiseFormError && (
              <div className="mt-4">
                <Notice role="alert" title={raiseFormError} />
              </div>
            )}

            <form onSubmit={(e) => { void handleRaiseSubmit(e) }} className="mt-5 space-y-4">
              {/* Scan selector: ONLY lists CONFIRMED scans */}
              <div>
                <label htmlFor="select-scan" className="block text-label text-mute">
                  Select confirmed inspection scan *
                </label>
                <select
                  id="select-scan"
                  value={selectedScanId}
                  onChange={(e) => handleScanSelectChange(e.target.value)}
                  required
                  className="input mt-1.5 font-mono"
                >
                  <option value="">Choose an officer-confirmed scan</option>
                  {confirmedEligibleSubmissions.map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.id} — Confirmed {sub.verdict ? verdictLabel(sub.verdict) : ''} ({sub.product_category || 'Commodity'})
                    </option>
                  ))}
                </select>
                <p className="mt-1.5 text-label text-mute">
                  Showing {confirmedEligibleSubmissions.length} inspections with confirmed verdicts. Unconfirmed machine scans are omitted.
                </p>
              </div>

              <div>
                <label htmlFor="mfr-name" className="block text-label text-mute">
                  Declared manufacturer name *
                </label>
                <input
                  id="mfr-name"
                  type="text"
                  value={manufacturerName}
                  onChange={(e) => setManufacturerName(e.target.value)}
                  required
                  placeholder="e.g. Apex Agro Refining Private Limited"
                  className="input mt-1.5"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="rule-id" className="block text-label text-mute">
                    Rule ID / clause reference *
                  </label>
                  <input
                    id="rule-id"
                    type="text"
                    value={ruleId}
                    onChange={(e) => setRuleId(e.target.value)}
                    required
                    placeholder="e.g. rule-6-1-d"
                    className="input mt-1.5 font-mono"
                  />
                </div>
                <div>
                  <label htmlFor="field-select" className="block text-label text-mute">
                    Declaration field *
                  </label>
                  <select
                    id="field-select"
                    value={field}
                    onChange={(e) => setField(e.target.value as DeclarationField)}
                    required
                    className="input mt-1.5 font-mono"
                  >
                    {DECLARATION_FIELDS.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="measured-value" className="block text-label text-mute">
                    Measured value (observed) *
                  </label>
                  <input
                    id="measured-value"
                    type="text"
                    value={measuredValue}
                    onChange={(e) => setMeasuredValue(e.target.value)}
                    required
                    placeholder="e.g. 480g"
                    className="input mt-1.5"
                  />
                </div>
                <div>
                  <label htmlFor="required-value" className="block text-label text-mute">
                    Required value (declared) *
                  </label>
                  <input
                    id="required-value"
                    type="text"
                    value={requiredValue}
                    onChange={(e) => setRequiredValue(e.target.value)}
                    required
                    placeholder="e.g. 500g"
                    className="input mt-1.5"
                  />
                </div>
              </div>

              <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end sm:gap-3">
                <button type="button" onClick={closeRaise} className="btn btn-ghost">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedScanId || raiseSubmitting}
                  className="btn btn-primary"
                >
                  {raiseSubmitting ? 'Submitting…' : 'Submit formal complaint'}
                </button>
              </div>
            </form>
          </Sheet>
        )}

        {/* Lifecycle transition (append-only event creation) */}
        {transitionTarget && (
          <Sheet
            key="transition"
            labelledBy="transition-title"
            onClose={() => setTransitionTarget(null)}
            width="sm:max-w-lg"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 id="transition-title" className="font-sans text-section">
                Record {statusLabel(transitionTarget.toStatus).toLowerCase()}
              </h2>
              <CloseButton onClick={() => setTransitionTarget(null)} />
            </div>

            <form onSubmit={handleTransitionSubmit} className="mt-3 space-y-4">
              <p className="text-secondary text-mute">
                Recording this transition writes a new immutable event row superseding{' '}
                <span className="font-mono font-medium text-ink [overflow-wrap:anywhere]">
                  #{transitionTarget.record.id}
                </span>
                .
              </p>

              <div>
                <label htmlFor="action-note" className="block text-label text-mute">
                  {transitionTarget.toStatus === 'acknowledged'
                    ? 'Manufacturer acknowledgement reference and details *'
                    : transitionTarget.toStatus === 'resolved'
                      ? 'Resolution summary and corrective undertaking *'
                      : 'Rejection grounds and verification findings *'}
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
                  className="input mt-1.5"
                />
              </div>

              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
                <button
                  type="button"
                  onClick={() => setTransitionTarget(null)}
                  className="btn btn-ghost"
                >
                  Cancel
                </button>
                <button type="submit" disabled={!actionNote.trim()} className="btn btn-primary">
                  Append {statusLabel(transitionTarget.toStatus).toLowerCase()} record
                </button>
              </div>
            </form>
          </Sheet>
        )}

        {/* Reopen complaint (UI Rule 3: append-only superseding event) */}
        {reopenTarget && (
          <Sheet
            key="reopen"
            labelledBy="reopen-title"
            onClose={() => setReopenTarget(null)}
            width="sm:max-w-lg"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 id="reopen-title" className="font-sans text-section [overflow-wrap:anywhere]">
                Reopen complaint #{reopenTarget.id}
              </h2>
              <CloseButton onClick={() => setReopenTarget(null)} />
            </div>

            <div className="mt-3 rounded-ctl bg-sunken/60 p-4 text-secondary text-mute">
              <p className="text-body font-medium text-ink">{reopenTarget.manufacturer_name}</p>
              <p className="font-mono text-label [overflow-wrap:anywhere]">
                Previous status: {statusLabel(reopenTarget.status)} · Supersedes #{reopenTarget.id}
              </p>
              <p className="mt-1.5">
                Reopening does not modify the existing record in place. It appends a new
                superseding event in raised status to the audit trail.
              </p>
            </div>

            {reopenError && (
              <div className="mt-3">
                <Notice role="alert" title={reopenError} />
              </div>
            )}

            <form onSubmit={handleReopenSubmit} className="mt-4 space-y-4">
              <div>
                <label htmlFor="reopen-justification" className="block text-label text-mute">
                  Reopening justification / new investigation evidence *
                </label>
                <textarea
                  id="reopen-justification"
                  rows={3}
                  value={reopenJustification}
                  onChange={(e) => setReopenJustification(e.target.value)}
                  required
                  placeholder="Detail subsequent inspection findings or persistence of package shortfall..."
                  className="input mt-1.5"
                />
              </div>

              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
                <button type="button" onClick={() => setReopenTarget(null)} className="btn btn-ghost">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!reopenJustification.trim()}
                  className="btn btn-primary"
                >
                  Append reopened complaint (raised)
                </button>
              </div>
            </form>
          </Sheet>
        )}
      </AnimatePresence>
    </div>
  )
}
