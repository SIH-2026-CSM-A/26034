import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { VerdictTag, verdictLabel } from './components/VerdictBanner'

type ScanSummary = components['schemas']['ScanSummary']
type Verdict = components['schemas']['Verdict']

/**
 * Review queue. Desktop, dense, sortable and filterable — built for clearing
 * inspections in a sitting, connected live to GET /scans via apiClient.
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

const COLUMNS: ReadonlyArray<{ key: SortKey; label: string; className: string }> = [
  { key: 'product', label: 'Product / Category', className: 'w-[26%]' },
  { key: 'verdict', label: 'Verdict', className: 'w-[18%]' },
  { key: 'status', label: 'Status', className: 'w-[14%]' },
  { key: 'created_at', label: 'Captured', className: 'w-[18%]' },
]

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
      const { data, error: apiError } = await apiClient.GET('/scans')
      if (apiError) {
        setError('Failed to fetch scans from API.')
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
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b-2 border-ink">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-center gap-x-6 gap-y-1 px-4 py-3">
          <span className="text-label text-mute">PCCS</span>
          <span className="text-label text-mute">Review queue</span>
          <div className="ml-auto flex items-center gap-3">
            <Link
              to="/officer/capture"
              className="flex min-h-target items-center border border-ink bg-paper px-3 py-1 font-mono text-label text-ink hover:bg-mute/10"
            >
              Camera
            </Link>
            <Link
              to="/officer/new"
              className="flex min-h-target items-center border border-ink bg-ink px-3 py-1 text-label text-paper hover:bg-ink/90"
            >
              + New scan
            </Link>
            <span className="font-mono text-label">
              {rows.length} of {scans.length} inspections
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1280px] px-4 pb-16">
        <h1 className="pt-6 text-title">Awaiting review</h1>
        <p className="mt-1 text-secondary text-mute">
          Every row is a recommendation pending officer confirmation. Live data from GET /scans.
        </p>

        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-4">
          <FilterSelect
            label="Verdict"
            value={verdictFilter}
            onChange={(value) => setVerdictFilter(value as Verdict | 'ALL')}
            options={[
              { value: 'ALL', label: 'All verdicts' },
              { value: 'POTENTIAL_VIOLATION', label: verdictLabel('POTENTIAL_VIOLATION') },
              { value: 'REVIEW', label: verdictLabel('REVIEW') },
              { value: 'PASS', label: verdictLabel('PASS') },
            ]}
          />
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
          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Product / Category</span>
            <input
              type="search"
              value={productQuery}
              onChange={(event) => setProductQuery(event.target.value)}
              placeholder="Filter by commodity or ID"
              className="min-h-target w-64 border border-ink bg-paper px-3 py-2 text-body placeholder:text-mute"
            />
          </label>
        </section>

        {loading && (
          <div className="mt-8 border border-hairline p-8 text-center">
            <p className="font-mono text-body text-mute animate-pulse">Loading inspection queue from API...</p>
          </div>
        )}

        {error && (
          <div className="mt-8 border border-seal bg-paper p-6">
            <p className="text-body font-semibold text-seal">Unable to load review queue</p>
            <p className="mt-1 text-secondary text-mute">{error}</p>
            <button
              type="button"
              onClick={fetchScans}
              className="mt-4 border border-ink px-4 py-2 text-label hover:bg-mute/10"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <table className="mt-6 w-full border-collapse text-left">
            <caption className="sr-only">
              Inspections awaiting review, sortable by product, verdict, status and
              capture time.
            </caption>
            <thead>
              <tr className="border-y-2 border-ink">
                {COLUMNS.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    className={`${column.className} p-0`}
                    aria-sort={
                      sortKey === column.key
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key)}
                      className="flex min-h-target w-full items-center gap-2 px-3 py-2 text-label"
                    >
                      {column.label}
                      <SortMark
                        active={sortKey === column.key}
                        direction={sortDirection}
                      />
                    </button>
                  </th>
                ))}
                <th scope="col" className="w-[12%] px-3 py-2 text-label">
                  Rule Set
                </th>
                <th scope="col" className="px-3 py-2 text-label">
                  Inspection
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-hairline align-middle">
                  <td className="px-3 py-2">
                    <span className="text-body font-medium">
                      {row.product_category ?? (row.source_type === 'physical_label' ? 'Physical label' : 'Catalogue record')}
                    </span>
                    <span className="ml-2 font-mono text-label text-mute">
                      {row.source_type}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    {row.verdict ? (
                      <VerdictTag verdict={row.verdict} />
                    ) : (
                      <span className="inline-block px-2 py-1 font-mono text-label text-mute border-y border-dashed border-mute">
                        {row.status.toUpperCase()}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-secondary">
                    {row.finalised ? 'Finalised' : row.status}
                  </td>
                  <td className="px-3 py-2 font-mono text-secondary">
                    {formatCaptured(row.created_at)}
                  </td>
                  <td className="px-3 py-2 font-mono text-secondary">
                    v{row.rule_set_version}
                  </td>
                  <td className="px-3 py-1">
                    <Link
                      to={`/officer/verdicts/${row.id}`}
                      className="flex min-h-target items-center whitespace-nowrap font-mono text-label underline underline-offset-4"
                    >
                      {row.id.slice(0, 8)}...
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {!loading && !error && rows.length === 0 && (
          <p className="mt-6 border border-dotted border-mute p-6 text-body text-mute">
            {scans.length === 0
              ? 'No inspections found in the queue.'
              : 'No inspections match these filters. Widen the verdict filter or clear the search.'}
          </p>
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
      <svg viewBox="0 0 12 12" aria-hidden="true" className="h-3 w-3 text-hairline" fill="none">
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
      <span className="text-label text-mute">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-target border border-ink bg-paper px-3 py-2 text-body"
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
