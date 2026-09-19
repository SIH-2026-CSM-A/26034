import { SEEDED_DEMO_OFFICER } from '../services/demo'
import { motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import { serverMessage } from '../services/errors'
import type { components } from '../services/generated/schema'
import { spring } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictTag, verdictLabel } from './components/VerdictBanner'

type ScanSummary = components['schemas']['ScanSummary']
type Verdict = components['schemas']['Verdict']

/**
 * Review queue. Sortable and filterable, connected live to GET /scans via
 * apiClient. A row is a card on a phone and a six-column line on a desktop, and
 * it is the shared element that opens into the verdict screen.
 *
 * Every measured or sortable value is set in mono so a column of timestamps
 * and ids read as columns rather than as ragged text.
 */

type SortKey = 'verdict' | 'product' | 'created_at' | 'status'
type SortDirection = 'asc' | 'desc'

/** Sort order for verdicts is by how much attention each one demands. */
const VERDICT_ORDER: Record<Verdict, number> = {
  POTENTIAL_VIOLATION: 0,
  REVIEW: 1,
  PASS: 2,
}

const COLUMNS: ReadonlyArray<{ key: SortKey; label: string }> = [
  { key: 'product', label: 'Product / Category' },
  { key: 'verdict', label: 'Verdict' },
  { key: 'status', label: 'Status' },
  { key: 'created_at', label: 'Captured' },
]

/** One template for the column heads, the skeleton and the rows, so they cannot drift. */
const ROW_GRID = 'grid-cols-[1fr_auto] md:grid-cols-[minmax(0,2.2fr)_minmax(0,1.7fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.7fr)_minmax(0,1fr)]'

const VERDICT_FILTERS: ReadonlyArray<Verdict | 'ALL'> = ['ALL', 'POTENTIAL_VIOLATION', 'REVIEW', 'PASS']

function compare(a: ScanSummary, b: ScanSummary, key: SortKey): number {
  switch (key) {
    case 'verdict': {
      const aRank = a.verdict ? VERDICT_ORDER[a.verdict] ?? 99 : 99
      const bRank = b.verdict ? VERDICT_ORDER[b.verdict] ?? 99 : 99
      return aRank - bRank
    }
    case 'product': {
      const aProd = a.product_category ?? a.source_type
      const bProd = b.product_category ?? b.source_type
      return aProd.localeCompare(bProd)
    }
    case 'created_at':
      return a.created_at.localeCompare(b.created_at)
    case 'status':
      return a.status.localeCompare(b.status)
  }
}

function formatCaptured(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function ReviewQueue() {
  const [sortKey, setSortKey] = useState<SortKey>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [verdictFilter, setVerdictFilter] = useState<Verdict | 'ALL'>('ALL')
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [productQuery, setProductQuery] = useState('')
  const [scans, setScans] = useState<ScanSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchScans = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError, response } = await apiClient.GET('/scans')
      if (apiError) {
        setError(serverMessage(apiError, response))
      } else if (data) {
        setScans(data)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Network error occurred.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchScans()
  }, [fetchScans])

  const rows = useMemo(() => {
    const query = productQuery.trim().toLowerCase()
    const filtered = scans.filter((row) => {
      if (verdictFilter !== 'ALL' && row.verdict !== verdictFilter) return false
      if (statusFilter !== 'ALL' && row.status !== statusFilter) return false
      if (query) {
        const prod = (row.product_category ?? '').toLowerCase()
        const src = row.source_type.toLowerCase()
        const id = row.id.toLowerCase()
        if (!prod.includes(query) && !src.includes(query) && !id.includes(query)) {
          return false
        }
      }
      return true
    })
    const sorted = [...filtered].sort((a, b) => compare(a, b, sortKey))
    return sortDirection === 'asc' ? sorted : sorted.reverse()
  }, [scans, sortKey, sortDirection, verdictFilter, statusFilter, productQuery])

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="Queue" />

      <main className="mx-auto max-w-[1280px] px-4 pb-28 pt-6 md:pb-16 md:pt-10">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
          <div>
            <h1 className="text-title">Awaiting review</h1>
            <p className="mt-1 text-secondary text-mute">
              Every row is a recommendation pending officer confirmation. Live data from GET /scans.
            </p>
          </div>
          {!loading && !error && (
            <p className="font-mono text-label text-mute">
              {rows.length} of {scans.length} inspections
            </p>
          )}
        </div>

        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-3">
          <div
            role="group"
            aria-label="Verdict"
            className="flex w-full gap-0.5 overflow-x-auto rounded-full border border-hairline/70 bg-sunken/70 p-1 [scrollbar-width:none] sm:w-auto [&::-webkit-scrollbar]:hidden"
          >
            {VERDICT_FILTERS.map((value) => {
              const active = verdictFilter === value
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setVerdictFilter(value)}
                  className={`relative min-h-[40px] flex-1 whitespace-nowrap rounded-full px-3.5 text-label transition-colors duration-base sm:flex-none ${
                    active ? 'text-ink' : 'text-mute hover:text-ink'
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="verdict-filter-pill"
                      transition={spring.snap}
                      className="absolute inset-0 rounded-full bg-surface shadow-e1"
                    />
                  )}
                  <span className="relative">{value === 'ALL' ? 'All' : verdictLabel(value)}</span>
                </button>
              )
            })}
          </div>
          <FilterSelect
            label="Status"
            value={statusFilter}
            onChange={(value) => setStatusFilter(value)}
            options={[
              { value: 'ALL', label: 'All statuses' },
              { value: 'complete', label: 'Complete' },
              { value: 'processing', label: 'Processing' },
              { value: 'received', label: 'Received' },
              { value: 'failed', label: 'Failed' },
            ]}
          />
          <label className="flex min-w-0 flex-1 flex-col gap-1 sm:max-w-xs">
            <span className="sr-only">Product / Category</span>
            <input
              type="search"
              value={productQuery}
              onChange={(event) => setProductQuery(event.target.value)}
              placeholder="Filter by commodity or ID"
              className="input"
            />
          </label>
        </section>

        {error && (
          <div className="mt-6">
            <Notice
              title="Unable to load review queue"
              role="alert"
              action={
                <button type="button" onClick={fetchScans} className="btn btn-quiet">
                  Retry
                </button>
              }
            >
              {error}
            </Notice>
          </div>
        )}

        {!error && (
          <div className="mt-6">
            {/* Column heads double as the sort controls. Hidden below md, where a row is a card. */}
            <div className={`hidden items-center px-5 pb-1 md:grid ${ROW_GRID}`}>
              {COLUMNS.map((column) => (
                <button
                  key={column.key}
                  type="button"
                  onClick={() => toggleSort(column.key)}
                  aria-label={`Sort by ${column.label}`}
                  aria-pressed={sortKey === column.key}
                  className="-ml-2 flex min-h-target items-center gap-2 rounded-ctl px-2 text-left text-label text-mute hover:text-ink"
                >
                  {column.label}
                  <SortMark active={sortKey === column.key} direction={sortDirection} />
                </button>
              ))}
              <span className="text-label text-mute">Rule set</span>
              <span className="text-label text-mute">Inspection</span>
            </div>

            {loading ? (
              <ul aria-busy="true" aria-label="Loading inspection queue" className="space-y-2.5">
                {[0, 1, 2, 3, 4, 5].map((i) => (
                  <li key={i} className={`card grid items-center gap-x-4 gap-y-3 px-5 py-4 md:min-h-[72px] md:py-2 ${ROW_GRID}`}>
                    <span className="skeleton col-span-2 h-5 w-40 md:col-span-1" />
                    <span className="skeleton col-span-2 h-7 w-28 rounded-full md:col-span-1" />
                    <span className="skeleton hidden h-4 w-20 md:block" />
                    <span className="skeleton h-4 w-20 md:hidden" />
                    <span className="skeleton h-4 w-28 justify-self-end md:justify-self-start" />
                    <span className="skeleton hidden h-4 w-12 md:block" />
                    <span className="skeleton hidden h-4 w-20 md:block" />
                  </li>
                ))}
              </ul>
            ) : (
              <ul className="space-y-2.5">
                {rows.map((row, index) => (
                  <motion.li
                    key={row.id}
                    layout
                    layoutId={`scan-${row.id}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...spring.glide, delay: Math.min(index, 12) * 0.03 }}
                    className="card card-lift"
                  >
                    <Link
                      to={`/officer/verdicts/${row.id}`}
                      state={{ summary: row }}
                      className={`grid items-center gap-x-4 gap-y-2 rounded-card px-5 py-4 md:min-h-[72px] md:py-2 ${ROW_GRID}`}
                    >
                      <span className="col-span-2 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 md:col-span-1">
                        <span className="text-body font-medium">
                          {row.product_category ??
                            (row.source_type === 'physical_label' ? 'Physical label' : 'Catalogue record')}
                        </span>
                        <span className="font-mono text-label text-mute">{row.source_type}</span>
                        {row.officer_id === SEEDED_DEMO_OFFICER && <span className="badge-seeded">seeded demo</span>}
                      </span>
                      <span className="col-span-2 md:col-span-1">
                        {row.verdict ? (
                          <VerdictTag verdict={row.verdict} />
                        ) : (
                          <span className="inline-block rounded-full border border-dotted border-mute px-2.5 py-1 font-mono text-label text-mute">
                            {row.status.toUpperCase()}
                          </span>
                        )}
                      </span>
                      <span className="font-mono text-label text-mute md:text-secondary md:text-ink">
                        <span className="md:hidden">Status </span>
                        {row.finalised ? 'Finalised' : row.status}
                      </span>
                      <span className="whitespace-nowrap text-right font-mono text-label text-mute md:text-left md:text-secondary md:text-ink">{formatCaptured(row.created_at)}</span>
                      <span className="hidden font-mono text-secondary md:block">v{row.rule_set_version}</span>
                      <span className="hidden items-center justify-between font-mono text-label text-mute md:flex">
                        {row.id.slice(0, 8)}
                        <svg viewBox="0 0 16 16" aria-hidden="true" className="h-4 w-4" fill="none">
                          <path d="m6 3.5 4.5 4.5L6 12.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </span>
                    </Link>
                  </motion.li>
                ))}
              </ul>
            )}
          </div>
        )}

        {!loading && !error && rows.length === 0 && (
          <Notice title={scans.length === 0 ? 'No inspections found in the queue.' : 'No inspections match these filters.'}>
            {scans.length === 0
              ? 'Submit a scan and it will appear here.'
              : 'Widen the verdict filter or clear the search.'}
          </Notice>
        )}
      </main>
    </div>
  )
}

/**
 * The sort indicator is a shape, not a colour and not a hover affordance.
 */
function SortMark({ active, direction }: { active: boolean; direction: SortDirection }) {
  if (!active) {
    return (
      <svg viewBox="0 0 12 12" aria-hidden="true" className="h-3 w-3 text-mute/50" fill="none">
        <path d="M6 1.5 9 5H3zM6 10.5 3 7h6z" fill="currentColor" />
      </svg>
    )
  }
  return (
    <svg viewBox="0 0 12 12" aria-hidden="true" className="h-3 w-3 text-ink" fill="none">
      {direction === 'asc' ? <path d="M6 1.5 10 7H2z" fill="currentColor" /> : <path d="M6 10.5 2 5h8z" fill="currentColor" />}
    </svg>
  )
}

interface FilterSelectProps {
  label: string
  value: string
  onChange: (value: string) => void
  options: ReadonlyArray<{ value: string; label: string }>
}

function FilterSelect({ label, value, onChange, options }: FilterSelectProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="input w-auto pr-8"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
