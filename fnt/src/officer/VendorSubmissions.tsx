import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { OfficerHeader } from './components/OfficerHeader'

type VendorResponse = components['schemas']['VendorResponse']
type VendorType = components['schemas']['VendorType']

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
  const [vendors, setVendors] = useState<VendorResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const [searchQuery, setSearchQuery] = useState('')
  const [vendorTypeFilter, setVendorTypeFilter] = useState<VendorType | 'ALL'>('ALL')
  const [districtFilter, setDistrictFilter] = useState<string>('ALL')

  useEffect(() => {
    let active = true
    async function loadVendors() {
      setLoading(true)
      setFetchError(null)
      try {
        const { data, error } = await apiClient.GET('/vendors')
        if (!active) return
        if (error || !data) {
          setFetchError('Could not load vendor register. Check your connection or try again.')
        } else {
          setVendors(data)
        }
      } catch {
        if (active) {
          setFetchError('Network error loading vendor register.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    loadVendors()
    return () => {
      active = false
    }
  }, [])

  // Unique districts for filter dropdown
  const districts = useMemo(() => {
    const set = new Set<string>()
    for (const v of vendors) {
      if (v.jurisdiction.district) set.add(v.jurisdiction.district)
    }
    return Array.from(set).sort()
  }, [vendors])

  // Metrics
  const metrics = useMemo(() => {
    const byType: Record<string, number> = { kirana: 0, supermarket: 0, godown: 0 }
    for (const v of vendors) {
      byType[v.vendor_type] = (byType[v.vendor_type] ?? 0) + 1
    }
    return {
      total: vendors.length,
      kirana: byType.kirana ?? 0,
      supermarket: byType.supermarket ?? 0,
      godown: byType.godown ?? 0,
    }
  }, [vendors])

  // Filtered rows
  const filteredVendors = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return vendors.filter((v) => {
      if (vendorTypeFilter !== 'ALL' && v.vendor_type !== vendorTypeFilter) return false
      if (districtFilter !== 'ALL' && v.jurisdiction.district !== districtFilter) return false
      if (q) {
        const matchesName = v.name.toLowerCase().includes(q)
        const matchesDistrict = (v.jurisdiction.district ?? '').toLowerCase().includes(q)
        const matchesState = v.jurisdiction.state.toLowerCase().includes(q)
        if (!matchesName && !matchesDistrict && !matchesState) return false
      }
      return true
    })
  }, [vendors, searchQuery, vendorTypeFilter, districtFilter])

  return (
    <div className="min-h-screen bg-paper text-ink">
      <OfficerHeader currentTitle="Vendor Submissions" />

      <main className="mx-auto max-w-[1280px] px-4 pb-16 pt-4">
        {/* Masthead & Title */}
        <div className="border-b border-ink pb-4">
          <h1 className="text-title">Vendor Register &amp; Jurisdictional Premises</h1>
          <p className="mt-1 text-secondary text-mute">
            Registered trading premises within this officer&apos;s jurisdiction under the Legal
            Metrology (Packaged Commodities) Rules, 2011.
          </p>

          {/* Metric Strip */}
          <div className="mt-4 grid grid-cols-2 gap-3 border border-hairline bg-paper p-3 sm:grid-cols-4">
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Total Premises</span>
              <span className="font-mono text-title font-semibold">{metrics.total}</span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Kirana Stores</span>
              <span className="font-mono text-title font-semibold">{metrics.kirana}</span>
            </div>
            <div className="border-r border-hairline/60 pr-2">
              <span className="block text-label text-mute">Supermarkets</span>
              <span className="font-mono text-title font-semibold">{metrics.supermarket}</span>
            </div>
            <div>
              <span className="block text-label text-mute">Godowns / Storage</span>
              <span className="font-mono text-title font-semibold">{metrics.godown}</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <section aria-label="Filters" className="mt-6 flex flex-wrap items-end gap-3 border-b border-hairline pb-4">
          <label className="flex flex-col gap-1">
            <span className="text-label text-mute">Search Premise</span>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, district, or state..."
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

          {(searchQuery || vendorTypeFilter !== 'ALL' || districtFilter !== 'ALL') && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setVendorTypeFilter('ALL')
                setDistrictFilter('ALL')
              }}
              className="min-h-target border border-hairline px-3 py-1.5 text-label text-mute hover:border-ink hover:text-ink"
            >
              Reset filters
            </button>
          )}
        </section>

        {/* List Header */}
        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-label text-mute">
            Showing {filteredVendors.length} of {vendors.length} premises
          </span>
          <span className="text-label text-mute">
            Legal Metrology (Packaged Commodities) Rules, 2011
          </span>
        </div>

        {/* Loading / Error / Empty / Table */}
        {loading ? (
          <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
            Loading vendor register…
          </div>
        ) : fetchError ? (
          <div
            role="alert"
            className="mt-6 border-2 border-seal bg-paper p-4 text-body text-seal"
          >
            {fetchError}
          </div>
        ) : filteredVendors.length === 0 ? (
          <div className="mt-6 border border-dashed border-mute p-8 text-center text-body text-mute">
            No vendor premises recorded in this jurisdiction.
          </div>
        ) : (
          <div className="mt-4">
            {/* Desktop Table */}
            <div className="hidden overflow-x-auto lg:block">
              <table className="w-full border-collapse text-left">
                <caption className="sr-only">
                  Registered vendor premises and statutory jurisdiction
                </caption>
                <thead>
                  <tr className="border-y-2 border-ink text-label">
                    <th scope="col" className="w-[30%] px-3 py-2">
                      Vendor / Premise
                    </th>
                    <th scope="col" className="w-[20%] px-3 py-2">
                      Premise Type
                    </th>
                    <th scope="col" className="w-[30%] px-3 py-2">
                      Jurisdiction (District, State)
                    </th>
                    <th scope="col" className="w-[20%] px-3 py-2 text-right">
                      Registered At
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVendors.map((vendor) => (
                    <tr
                      key={vendor.id}
                      className="border-b border-hairline transition-colors hover:bg-focus-tint/20"
                    >
                      {/* Vendor name */}
                      <td className="px-3 py-3 align-top">
                        <p className="text-body font-medium text-ink">{vendor.name}</p>
                        <p className="font-mono text-label text-mute">{vendor.id}</p>
                      </td>

                      {/* Type */}
                      <td className="px-3 py-3 align-top">
                        <span className="border border-hairline px-1.5 py-0.5 font-mono text-label uppercase text-mute">
                          {vendorTypeLabel(vendor.vendor_type)}
                        </span>
                      </td>

                      {/* Jurisdiction */}
                      <td className="px-3 py-3 align-top">
                        <p className="text-body text-ink">
                          {[vendor.jurisdiction.district, vendor.jurisdiction.region, vendor.jurisdiction.state]
                            .filter(Boolean)
                            .join(', ')}
                        </p>
                      </td>

                      {/* Registered at */}
                      <td className="px-3 py-3 text-right align-top font-mono text-label text-mute">
                        {formatTimestamp(vendor.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="space-y-4 lg:hidden">
              {filteredVendors.map((vendor) => (
                <article
                  key={vendor.id}
                  className="border-b-2 border-ink pb-4 pt-2"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h2 className="text-body font-semibold text-ink">{vendor.name}</h2>
                      <span className="mt-0.5 inline-block border border-hairline px-1.5 py-0.5 font-mono text-label uppercase text-mute">
                        {vendorTypeLabel(vendor.vendor_type)}
                      </span>
                    </div>
                    <span className="font-mono text-label text-mute">
                      {formatTimestamp(vendor.created_at)}
                    </span>
                  </div>

                  <div className="mt-3 border-t border-hairline pt-2">
                    <p className="text-secondary text-mute">
                      Jurisdiction:{' '}
                      {[vendor.jurisdiction.district, vendor.jurisdiction.region, vendor.jurisdiction.state]
                        .filter(Boolean)
                        .join(', ')}
                    </p>
                    <p className="mt-1 font-mono text-label text-mute">{vendor.id}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
