import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Verdict } from '../fixtures/contracts'
import { queueRows, type QueueRow } from '../fixtures/review-queue.fixture'
import { VerdictTag, verdictLabel } from './components/VerdictBanner'

/**
 * Review queue. Desktop, dense, sortable and filterable — built for clearing
 * forty inspections in a sitting, not for looking good with six.
 *
 * Every measured or sortable value is set in mono so a column of confidences
 * and a column of timestamps read as columns rather than as ragged text.
 */

type SortKey = 'verdict' | 'confidence' | 'product' | 'captured_at'
type SortDirection = 'asc' | 'desc'

/** Sort order for verdicts is by how much attention each one demands. */
const VERDICT_ORDER: Record<Verdict, number> = {
  [Verdict.POTENTIAL_VIOLATION]: 0,
  [Verdict.REVIEW]: 1,
  [Verdict.PASS]: 2,
}

const COLUMNS: ReadonlyArray<{ key: SortKey; label: string; className: string }> = [
  { key: 'product', label: 'Product', className: 'w-[24%]' },
  { key: 'verdict', label: 'Verdict', className: 'w-[18%]' },
  { key: 'confidence', label: 'Confidence', className: 'w-[13%]' },
  { key: 'captured_at', label: 'Captured', className: 'w-[16%]' },
]

function compare(a: QueueRow, b: QueueRow, key: SortKey): number {
  switch (key) {
    case 'verdict':
      return VERDICT_ORDER[a.verdict] - VERDICT_ORDER[b.verdict]
    case 'confidence':
      // A row with no confidence claim sorts last in either direction: it is
      // not a low score, it is the absence of a score, and letting it sit at
      // the top of an ascending sort would read as the worst reading.
      if (a.confidence === null || b.confidence === null) {
        return (a.confidence === null ? 1 : 0) - (b.confidence === null ? 1 : 0)
      }
      return a.confidence - b.confidence
    case 'product':
      return a.product.localeCompare(b.product)
    case 'captured_at':
      return a.captured_at.localeCompare(b.captured_at)
  }
}

function formatCaptured(iso: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  }).format(new Date(iso))
}

export function ReviewQueue() {
  const [sortKey, setSortKey] = useState<SortKey>('captured_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [verdictFilter, setVerdictFilter] = useState<Verdict | 'ALL'>('ALL')
  const [minConfidence, setMinConfidence] = useState<'ALL' | 'BELOW_80' | 'NO_CLAIM'>('ALL')
  const [productQuery, setProductQuery] = useState('')

  const rows = useMemo(() => {
    const query = productQuery.trim().toLowerCase()
    const filtered = queueRows.filter((row) => {
      if (verdictFilter !== 'ALL' && row.verdict !== verdictFilter) return false
      if (minConfidence === 'BELOW_80' && !(row.confidence !== null && row.confidence < 0.8)) {
        return false
      }
      if (minConfidence === 'NO_CLAIM' && row.confidence !== null) return false
      if (query && !row.product.toLowerCase().includes(query)) return false
      return true
    })
    const sorted = [...filtered].sort((a, b) => compare(a, b, sortKey))
    return sortDirection === 'asc' ? sorted : sorted.reverse()
  }, [sortKey, sortDirection, verdictFilter, minConfidence, productQuery])

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
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-baseline gap-x-6 gap-y-1 px-4 py-3">
          <span className="text-label text-mute">PCCS</span>
          <span className="text-label text-mute">Review queue</span>
          <span className="ml-auto font-mono text-label">
            {rows.length} of {queueRows.length} inspections
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-[1280px] px-4 pb-16">
        <h1 className="pt-6 text-title">Awaiting review</h1>
        <p className="mt-1 text-secondary text-mute">
          Every row is a recommendation pending officer confirmation.
        </p>

        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-4">
          <FilterSelect
            label="Verdict"
            value={verdictFilter}
            onChange={(value) => setVerdictFilter(value as Verdict | 'ALL')}
            options={[
              { value: 'ALL', label: 'All verdicts' },
              { value: Verdict.POTENTIAL_VIOLATION, label: verdictLabel(Verdict.POTENTIAL_VIOLATION) },
              { value: Verdict.REVIEW, label: verdictLabel(Verdict.REVIEW) },
              { value: Verdict.PASS, label: verdictLabel(Verdict.PASS) },
            ]}
          />
          <FilterSelect
            label="Confidence"
            value={minConfidence}
            onChange={(value) => setMinConfidence(value as 'ALL' | 'BELOW_80' | 'NO_CLAIM')}
            options={[
              { value: 'ALL', label: 'Any confidence' },
              { value: 'BELOW_80', label: 'Below 0.80' },
              { value: 'NO_CLAIM', label: 'No confidence claim' },
            ]}
          />
          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Product</span>
            <input
              type="search"
              value={productQuery}
              onChange={(event) => setProductQuery(event.target.value)}
              placeholder="Filter by commodity"
              className="min-h-target w-64 border border-ink bg-paper px-3 py-2 text-body placeholder:text-mute"
            />
          </label>
        </section>

        <table className="mt-6 w-full border-collapse text-left">
          <caption className="sr-only">
            Inspections awaiting review, sortable by product, verdict, confidence and
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
              <th scope="col" className="w-[8%] px-3 py-2 text-label">
                Open
              </th>
              <th scope="col" className="px-3 py-2 text-label">
                Inspection
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.subject_ref} className="border-b border-hairline align-middle">
                <td className="px-3 py-2">
                  <span className="text-body">{row.product}</span>
                  <span className="ml-2 font-mono text-label text-mute">
                    {row.declared_quantity}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <VerdictTag verdict={row.verdict} />
                </td>
                <td className="px-3 py-2 font-mono text-secondary">
                  {row.confidence === null ? (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">No confidence claim.</span>
                    </>
                  ) : (
                    row.confidence.toFixed(2)
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-secondary">
                  {formatCaptured(row.captured_at)}
                </td>
                <td className="px-3 py-2 font-mono text-secondary">{row.open_findings}</td>
                <td className="px-3 py-1">
                  <Link
                    to={`/officer/verdicts/${row.subject_ref}`}
                    className="flex min-h-target items-center whitespace-nowrap font-mono text-label underline underline-offset-4"
                  >
                    {row.subject_ref}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows.length === 0 && (
          <p className="mt-6 border border-dotted border-mute p-6 text-body text-mute">
            No inspections match these filters. Widen the verdict or confidence filter, or
            clear the product search.
          </p>
        )}
      </main>
    </div>
  )
}

/**
 * The sort indicator is a shape, not a colour and not a hover affordance —
 * hover is not available on the device half this product runs on, and
 * `aria-sort` on the header carries the same fact for assistive technology.
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
