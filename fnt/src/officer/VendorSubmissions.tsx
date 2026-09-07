import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { OfficerHeader } from './components/OfficerHeader'
import { VerdictTag } from './components/VerdictBanner'

export type Verdict = 'PASS' | 'REVIEW' | 'POTENTIAL_VIOLATION'
export type VendorType = 'godown' | 'supermarket' | 'kirana'

export interface Vendor {
  id: string
  name: string
  vendor_type: VendorType
  state: string
  region: string | null
  district: string | null
  address: string
  created_at: string
}

export interface RoutedOfficer {
  officer_id: string
  name: string
  designation: string
  jurisdiction_level: 'district' | 'region' | 'state'
  jurisdiction: string
}

export interface OfficerConfirmation {
  is_confirmed: boolean
  action: 'confirm' | 'reject' | 'override' | null
  officer_id: string | null
  confirmed_verdict: Verdict | null
  confirmed_at: string | null
  notes: string | null
}

export interface VendorSubmissionItem {
  scan_id: string
  verdict_id: string
  vendor: Vendor
  product_description: string
  product_category: 'food' | 'cosmetics' | 'medical_device'
  source_type: 'physical_label' | 'catalogue_record'
  captured_at: string
  recommended_verdict: Verdict
  routed_officer: RoutedOfficer
  officer_confirmation: OfficerConfirmation
  manufacturer_name: string
  issue_summary: string
  finding_counts: {
    pass: number
    review_required: number
    fail: number
    insufficient_evidence: number
    not_applicable: number
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

function vendorTypeLabel(type: VendorType): string {
  switch (type) {
    case 'kirana':
      return 'Kirana Store'
    case 'supermarket':
      return 'Supermarket'
    case 'godown':
      return 'Godown / Storage'
  }
}

export function VendorSubmissions() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [vendorTypeFilter, setVendorTypeFilter] = useState<VendorType | 'ALL'>('ALL')
  const [verdictFilter, setVerdictFilter] = useState<Verdict | 'ALL'>('ALL')
  const [confirmationFilter, setConfirmationFilter] = useState<'ALL' | 'CONFIRMED' | 'PENDING'>('ALL')
  const [districtFilter, setDistrictFilter] = useState<string>('ALL')
  const [selectedItem, setSelectedItem] = useState<VendorSubmissionItem | null>(null)

  // GET /vendors is currently unserved.
  const [submissions, setSubmissions] = useState<VendorSubmissionItem[]>([])
  void setSubmissions

  // Unique districts for filter dropdown
  const districts = useMemo(() => {
    const set = new Set<string>()
    for (const sub of submissions) {
      if (sub.vendor.district) set.add(sub.vendor.district)
    }
    return Array.from(set).sort()
  }, [submissions])

  // Metrics
  const metrics = useMemo(() => {
    const total = submissions.length
    let confirmedCount = 0
    let pendingCount = 0
    let potentialViolations = 0
    let reviews = 0
    let passes = 0

    for (const sub of submissions) {
      if (sub.officer_confirmation.is_confirmed) {
        confirmedCount++
      } else {
        pendingCount++
      }
      if (sub.recommended_verdict === 'POTENTIAL_VIOLATION') potentialViolations++
      else if (sub.recommended_verdict === 'REVIEW') reviews++
      else if (sub.recommended_verdict === 'PASS') passes++
    }

    return {
      total,
      confirmedCount,
      pendingCount,
      potentialViolations,
      reviews,
      passes,
    }
  }, [submissions])

  // Filtered rows
  const filteredSubmissions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return submissions.filter((item) => {
      if (vendorTypeFilter !== 'ALL' && item.vendor.vendor_type !== vendorTypeFilter) {
        return false
      }
      if (verdictFilter !== 'ALL' && item.recommended_verdict !== verdictFilter) {
        return false
      }
      if (confirmationFilter === 'CONFIRMED' && !item.officer_confirmation.is_confirmed) {
        return false
      }
      if (confirmationFilter === 'PENDING' && item.officer_confirmation.is_confirmed) {
        return false
      }
      if (districtFilter !== 'ALL' && item.vendor.district !== districtFilter) {
        return false
      }
      if (q) {
        const matchesVendor = item.vendor.name.toLowerCase().includes(q)
        const matchesScanId = item.scan_id.toLowerCase().includes(q)
        const matchesProd = item.product_description.toLowerCase().includes(q)
        const matchesOfficer = item.routed_officer.name.toLowerCase().includes(q)
        const matchesOfficerId = item.routed_officer.officer_id.toLowerCase().includes(q)
        if (
          !matchesVendor &&
          !matchesScanId &&
          !matchesProd &&
          !matchesOfficer &&
          !matchesOfficerId
        ) {
          return false
        }
      }
      return true
    })
  }, [submissions, searchQuery, vendorTypeFilter, verdictFilter, confirmationFilter, districtFilter])

  return (
    <div className="min-h-screen bg-paper text-ink">
      <OfficerHeader currentTitle="Vendor Submissions" />

      <main className="mx-auto max-w-[1280px] px-4 pb-16 pt-4">
        {/* Masthead & Title */}
        <div className="border-b border-ink pb-4">
          <h1 className="text-title">Vendor Submissions & Jurisdictional Routing</h1>
          <p className="mt-1 text-secondary text-mute">
            Packaged commodity scans attributed to physical premises and structured listings,
            automatically routed to designated Legal Metrology officers by statutory jurisdiction.
          </p>

          {/* Metric Strip */}
          <div className="mt-4 grid grid-cols-2 gap-3 border border-hairline bg-paper p-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Total Submissions</span>
              <span className="font-mono text-title font-semibold">{metrics.total}</span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Officer Confirmed</span>
              <span className="font-mono text-title font-semibold text-attest">
                {metrics.confirmedCount}
              </span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Pending Confirmation</span>
              <span className="font-mono text-title font-semibold text-query">
                {metrics.pendingCount}
              </span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">POTENTIAL VIOLATION</span>
              <span className="font-mono text-title font-semibold text-seal">
                {metrics.potentialViolations}
              </span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">REVIEW</span>
              <span className="font-mono text-title font-semibold text-query">
                {metrics.reviews}
              </span>
            </div>
            <div>
              <span className="block text-label text-mute">PASS</span>
              <span className="font-mono text-title font-semibold text-attest">
                {metrics.passes}
              </span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-3 border-b border-hairline pb-4">
          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Search Premise or Scan</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search vendor, scan ID, or commodity..."
              className="min-h-target w-64 border border-ink bg-paper px-3 py-1.5 text-body placeholder:text-mute"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Vendor Premise Type</span>
            <select
              value={vendorTypeFilter}
              onChange={(e) => setVendorTypeFilter(e.target.value as VendorType | 'ALL')}
              className="min-h-target border border-ink bg-paper px-3 py-1.5 text-body"
            >
              <option value="ALL">All Premise Types</option>
              <option value="kirana">Kirana Store</option>
              <option value="supermarket">Supermarket</option>
              <option value="godown">Godown / Storage</option>
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Recommended Verdict</span>
            <select
              value={verdictFilter}
              onChange={(e) => setVerdictFilter(e.target.value as Verdict | 'ALL')}
              className="min-h-target border border-ink bg-paper px-3 py-1.5 text-body"
            >
              <option value="ALL">All Verdicts</option>
              <option value="POTENTIAL_VIOLATION">POTENTIAL VIOLATION</option>
              <option value="REVIEW">REVIEW</option>
              <option value="PASS">PASS</option>
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Human Confirmation</span>
            <select
              value={confirmationFilter}
              onChange={(e) =>
                setConfirmationFilter(e.target.value as 'ALL' | 'CONFIRMED' | 'PENDING')
              }
              className="min-h-target border border-ink bg-paper px-3 py-1.5 text-body"
            >
              <option value="ALL">All States</option>
              <option value="CONFIRMED">Officer Confirmed</option>
              <option value="PENDING">Pending Confirmation</option>
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">District Jurisdiction</span>
            <select
              value={districtFilter}
              onChange={(e) => setDistrictFilter(e.target.value)}
              className="min-h-target border border-ink bg-paper px-3 py-1.5 text-body"
            >
              <option value="ALL">All Districts</option>
              {districts.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          {(searchQuery ||
            vendorTypeFilter !== 'ALL' ||
            verdictFilter !== 'ALL' ||
            confirmationFilter !== 'ALL' ||
            districtFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setVendorTypeFilter('ALL')
                setVerdictFilter('ALL')
                setConfirmationFilter('ALL')
                setDistrictFilter('ALL')
              }}
              className="min-h-target border border-hairline px-3 py-1.5 text-label text-mute hover:border-ink hover:text-ink"
            >
              Reset filters
            </button>
          )}
        </section>

        {/* Submissions List Header */}
        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-label text-mute">
            Showing {filteredSubmissions.length} of {submissions.length} submissions
          </span>
          <span className="text-label text-mute">
            Legal Metrology (Packaged Commodities) Rules, 2011
          </span>
        </div>

        {/* Submissions Table / Cards */}
        {filteredSubmissions.length === 0 ? (
          <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
            No vendor submissions recorded in this jurisdiction.
          </div>
        ) : (
          <div className="mt-4">
            {/* Desktop Table */}
            <div className="hidden overflow-x-auto lg:block">
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">
                  Vendor submissions and statutory jurisdiction routing
                </caption>
                <thead>
                  <tr className="border-y-2 border-ink text-label">
                    <th scope="col" className="w-[24%] px-3 py-2">
                      Vendor / Premise
                    </th>
                    <th scope="col" className="w-[22%] px-3 py-2">
                      Scan & Commodity
                    </th>
                    <th scope="col" className="w-[20%] px-3 py-2">
                      Recommended Verdict
                    </th>
                    <th scope="col" className="w-[20%] px-3 py-2">
                      Routed Officer (Jurisdiction)
                    </th>
                    <th scope="col" className="w-[14%] px-3 py-2 text-right">
                      Enforcement Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSubmissions.map((item) => {
                    const isConfirmed = item.officer_confirmation.is_confirmed

                    return (
                      <tr
                        key={item.scan_id}
                        className="border-b border-hairline transition-colors hover:bg-focus-tint/20"
                      >
                        {/* Vendor details */}
                        <td className="px-3 py-3 align-top">
                          <p className="text-body font-medium text-ink">{item.vendor.name}</p>
                          <div className="mt-1 flex items-center gap-2">
                            <span className="border border-hairline px-1.5 py-0.5 font-mono text-label uppercase text-mute">
                              {vendorTypeLabel(item.vendor.vendor_type)}
                            </span>
                            <span className="font-mono text-label text-mute">
                              {item.vendor.district}, {item.vendor.state}
                            </span>
                          </div>
                        </td>

                        {/* Scan details */}
                        <td className="px-3 py-3 align-top">
                          <p className="text-body text-ink">{item.product_description}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-x-2 font-mono text-label text-mute">
                            <span>ID: {item.scan_id}</span>
                            <span>•</span>
                            <span>{formatTimestamp(item.captured_at)}</span>
                          </div>
                        </td>

                        {/* Verdict & Human Confirmation */}
                        <td className="px-3 py-3 align-top">
                          <div>
                            <VerdictTag verdict={item.recommended_verdict} />
                          </div>
                          <div className="mt-2">
                            {isConfirmed ? (
                              <div className="flex flex-col gap-0.5">
                                <span className="inline-flex w-fit items-center gap-1 border border-attest bg-paper px-1.5 py-0.5 font-mono text-label font-medium text-attest">
                                  <span>✓</span>
                                  <span>OFFICER CONFIRMED</span>
                                </span>
                                <span className="font-mono text-label text-mute">
                                  Action: {item.officer_confirmation.action?.toUpperCase()} by{' '}
                                  {item.officer_confirmation.officer_id}
                                </span>
                              </div>
                            ) : (
                              <div className="flex flex-col gap-0.5">
                                <span className="inline-flex w-fit items-center gap-1 border border-dashed border-query bg-paper px-1.5 py-0.5 font-mono text-label font-medium text-query">
                                  <span>?</span>
                                  <span>PENDING CONFIRMATION</span>
                                </span>
                                <span className="text-label text-mute">
                                  Raw machine recommendation
                                </span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Routed Officer */}
                        <td className="px-3 py-3 align-top">
                          <p className="text-body font-medium text-ink">
                            {item.routed_officer.name}
                          </p>
                          <p className="text-secondary text-mute">
                            {item.routed_officer.designation}
                          </p>
                          <p className="mt-0.5 font-mono text-label text-mute">
                            {item.routed_officer.officer_id} • {item.routed_officer.jurisdiction}
                          </p>
                        </td>

                        {/* Actions */}
                        <td className="px-3 py-3 text-right align-top">
                          <div className="flex flex-col items-end gap-2">
                            <button
                              type="button"
                              onClick={() => setSelectedItem(item)}
                              className="min-h-target text-label text-ink underline underline-offset-4 hover:text-mute"
                            >
                              View details
                            </button>

                            {/* UI Rule 1 Strict Enforcement:
                                A complaint can ONLY be raised from a verdict that an officer has explicitly confirmed.
                                The UI must strictly forbid and hide the "Raise Complaint" path for raw machine verdicts. */}
                            {isConfirmed ? (
                              <button
                                type="button"
                                onClick={() =>
                                  navigate(`/officer/complaints?raise_scan_id=${item.scan_id}`)
                                }
                                className="flex min-h-target items-center border border-ink bg-ink px-3 py-1 text-label font-medium text-paper hover:bg-ink/90 active:bg-ink/80"
                              >
                                Raise Complaint →
                              </button>
                            ) : (
                              <div className="text-right">
                                <span
                                  title="Statutory constraint: A complaint cannot be raised against a raw machine verdict until an officer explicitly confirms it."
                                  className="inline-block border border-dashed border-mute px-2 py-1 text-label text-mute"
                                >
                                  Escalation locked
                                </span>
                                <p className="mt-0.5 text-label text-mute">
                                  Requires human confirmation
                                </p>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile / Responsive Cards (Down to 390px) */}
            <div className="space-y-4 lg:hidden">
              {filteredSubmissions.map((item) => {
                const isConfirmed = item.officer_confirmation.is_confirmed

                return (
                  <article
                    key={item.scan_id}
                    className="border-b-2 border-ink pb-4 pt-2"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h2 className="text-body font-semibold text-ink">{item.vendor.name}</h2>
                        <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                          <span className="border border-hairline px-1.5 py-0.5 font-mono text-label uppercase text-mute">
                            {vendorTypeLabel(item.vendor.vendor_type)}
                          </span>
                          <span className="font-mono text-label text-mute">
                            {item.vendor.district}, {item.vendor.state}
                          </span>
                        </div>
                      </div>
                      <VerdictTag verdict={item.recommended_verdict} />
                    </div>

                    <div className="mt-3 space-y-1.5 border-t border-hairline pt-2 text-secondary">
                      <p className="font-medium text-ink">{item.product_description}</p>
                      <p className="font-mono text-label text-mute">
                        Scan ID: {item.scan_id} • {formatTimestamp(item.captured_at)}
                      </p>

                      <div className="mt-2 border border-hairline bg-paper p-2">
                        <span className="block text-label text-mute">
                          Jurisdiction Routing:
                        </span>
                        <p className="text-body font-medium text-ink">
                          {item.routed_officer.name} ({item.routed_officer.designation})
                        </p>
                        <p className="font-mono text-label text-mute">
                          {item.routed_officer.officer_id} • {item.routed_officer.jurisdiction}
                        </p>
                      </div>

                      <div className="mt-2">
                        {isConfirmed ? (
                          <div className="flex items-center gap-2 text-attest">
                            <span className="border border-attest px-1.5 py-0.5 font-mono text-label font-semibold">
                              ✓ OFFICER CONFIRMED
                            </span>
                            <span className="font-mono text-label text-mute">
                              Action: {item.officer_confirmation.action?.toUpperCase()}
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-query">
                            <span className="border border-dashed border-query px-1.5 py-0.5 font-mono text-label font-semibold">
                              ? PENDING CONFIRMATION
                            </span>
                            <span className="text-label text-mute">
                              Machine recommendation
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-hairline/60 pt-2">
                      <button
                        type="button"
                        onClick={() => setSelectedItem(item)}
                        className="min-h-target text-label text-ink underline underline-offset-4"
                      >
                        Inspect details
                      </button>

                      {/* UI Rule 1 Strict Enforcement */}
                      {isConfirmed ? (
                        <button
                          type="button"
                          onClick={() =>
                            navigate(`/officer/complaints?raise_scan_id=${item.scan_id}`)
                          }
                          className="flex min-h-target items-center border border-ink bg-ink px-4 py-2 text-label font-medium text-paper hover:bg-ink/90"
                        >
                          Raise Complaint →
                        </button>
                      ) : (
                        <span className="border border-dashed border-mute px-2 py-1 text-label text-mute">
                          Escalation locked (Human confirmation required)
                        </span>
                      )}
                    </div>
                  </article>
                )
              })}
            </div>
          </div>
        )}

        {/* Modal: Submission Detail Drawer */}
        {selectedItem && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="submission-detail-title"
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
          >
            <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto border-2 border-ink bg-paper p-5 sm:p-6">
              <div className="flex items-start justify-between border-b border-ink pb-3">
                <div>
                  <span className="font-mono text-label text-mute">
                    INSPECTION REFERENCE: {selectedItem.scan_id}
                  </span>
                  <h2 id="submission-detail-title" className="text-section font-semibold">
                    {selectedItem.vendor.name}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="flex min-h-target items-center px-3 font-mono text-body hover:text-mute"
                  aria-label="Close modal"
                >
                  ✕
                </button>
              </div>

              <div className="mt-4 space-y-4">
                {/* Premise & Address */}
                <section>
                  <h3 className="text-label text-mute">Trading Premise</h3>
                  <p className="text-body font-medium">{selectedItem.vendor.name}</p>
                  <p className="text-secondary text-mute">{selectedItem.vendor.address}</p>
                  <p className="font-mono text-label text-mute">
                    Territory: {selectedItem.vendor.district}, {selectedItem.vendor.region},{' '}
                    {selectedItem.vendor.state}
                  </p>
                </section>

                {/* Scan & Product */}
                <section className="border-t border-hairline pt-3">
                  <h3 className="text-label text-mute">Commodity & Recommendation</h3>
                  <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-body font-medium">{selectedItem.product_description}</p>
                      <p className="text-secondary text-mute">
                        Declared Manufacturer: {selectedItem.manufacturer_name}
                      </p>
                    </div>
                    <VerdictTag verdict={selectedItem.recommended_verdict} />
                  </div>
                  <p className="mt-2 text-secondary text-mute">
                    Observation: {selectedItem.issue_summary}
                  </p>
                </section>

                {/* Jurisdiction Routing Detail */}
                <section className="border-t border-hairline pt-3">
                  <h3 className="text-label text-mute">Statutory Jurisdiction Routing</h3>
                  <div className="mt-1 border border-hairline bg-paper p-3 font-mono text-secondary">
                    <p className="text-body font-medium text-ink">
                      {selectedItem.routed_officer.name}
                    </p>
                    <p className="text-label text-mute">
                      Designation: {selectedItem.routed_officer.designation}
                    </p>
                    <p className="text-label text-mute">
                      Officer ID: {selectedItem.routed_officer.officer_id}
                    </p>
                    <p className="text-label text-mute">
                      Jurisdiction: {selectedItem.routed_officer.jurisdiction} (Level:{' '}
                      {selectedItem.routed_officer.jurisdiction_level})
                    </p>
                  </div>
                </section>

                {/* Confirmation Status */}
                <section className="border-t border-hairline pt-3">
                  <h3 className="text-label text-mute">Human Officer Confirmation</h3>
                  {selectedItem.officer_confirmation.is_confirmed ? (
                    <div className="mt-1 border border-attest bg-paper p-3 text-attest">
                      <p className="font-mono text-label font-bold">
                        VERDICT EXPLICITLY CONFIRMED BY OFFICER
                      </p>
                      <p className="mt-1 font-mono text-label text-ink">
                        Officer: {selectedItem.officer_confirmation.officer_id} • Action:{' '}
                        {selectedItem.officer_confirmation.action?.toUpperCase()} • At:{' '}
                        {selectedItem.officer_confirmation.confirmed_at
                          ? formatTimestamp(selectedItem.officer_confirmation.confirmed_at)
                          : '—'}
                      </p>
                      {selectedItem.officer_confirmation.notes && (
                        <p className="mt-1 text-secondary text-mute">
                          Notes: {selectedItem.officer_confirmation.notes}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="mt-1 border border-dashed border-query bg-paper p-3 text-query">
                      <p className="font-mono text-label font-bold">
                        PENDING OFFICER CONFIRMATION (RAW MACHINE RECOMMENDATION)
                      </p>
                      <p className="mt-1 text-secondary text-ink">
                        Under Legal Metrology Rules, 2011, machine recommendations cannot trigger
                        statutory escalation until confirmed by an authorized officer.
                      </p>
                    </div>
                  )}
                </section>
              </div>

              {/* Modal Actions */}
              <div className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-ink pt-4">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="min-h-target px-4 py-2 text-label text-mute hover:text-ink"
                >
                  Close
                </button>
                <Link
                  to={`/officer/verdicts/${selectedItem.scan_id}`}
                  className="flex min-h-target items-center border border-ink bg-paper px-4 py-2 font-mono text-label text-ink hover:bg-mute/10"
                >
                  Inspect scan details →
                </Link>

                {/* UI Rule 1 Strict Enforcement in Modal */}
                {selectedItem.officer_confirmation.is_confirmed ? (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedItem(null)
                      navigate(`/officer/complaints?raise_scan_id=${selectedItem.scan_id}`)
                    }}
                    className="flex min-h-target items-center border border-ink bg-ink px-4 py-2 font-medium text-label text-paper hover:bg-ink/90"
                  >
                    Proceed to Raise Complaint →
                  </button>
                ) : (
                  <span className="border border-dashed border-mute px-3 py-2 text-label text-mute">
                    Escalation locked (Pending human confirmation)
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
