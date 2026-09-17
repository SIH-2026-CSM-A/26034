import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { CountUp } from '../ui/CountUp'
import { rise, spring, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'
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

const TYPE_FILTERS: ReadonlyArray<{ value: VendorType | 'ALL'; label: string }> = [
  { value: 'ALL', label: 'All' },
  { value: 'kirana', label: 'Kirana' },
  { value: 'supermarket', label: 'Supermarket' },
  { value: 'godown', label: 'Godown' },
]

function jurisdictionLine(vendor: VendorResponse): string {
  return [vendor.jurisdiction.district, vendor.jurisdiction.region, vendor.jurisdiction.state]
    .filter(Boolean)
    .join(', ')
}

function TypeChip({ type }: { type: VendorType }) {
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-full border border-hairline bg-sunken/60 px-2.5 py-1 text-label text-mute">
      {vendorTypeLabel(type)}
    </span>
  )
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

  const districts = useMemo(() => {
    const set = new Set<string>()
    for (const v of vendors) {
      if (v.jurisdiction.district) set.add(v.jurisdiction.district)
    }
    return Array.from(set).sort()
  }, [vendors])

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

  const filtersActive = Boolean(searchQuery) || vendorTypeFilter !== 'ALL' || districtFilter !== 'ALL'
  const tiles: ReadonlyArray<{ label: string; value: number }> = [
    { label: 'Total premises', value: metrics.total },
    { label: 'Kirana stores', value: metrics.kirana },
    { label: 'Supermarkets', value: metrics.supermarket },
    { label: 'Godowns / storage', value: metrics.godown },
  ]

  return (
    <div className="aurora">
      <OfficerHeader currentTitle="Vendor submissions" />

      <main className="mx-auto max-w-[1280px] px-4 pb-28 pt-6 md:pb-16">
        <h1 className="text-title">Vendor register and jurisdictional premises</h1>
        <p className="mt-2 max-w-[720px] text-secondary text-mute">
          Registered trading premises within this officer&apos;s jurisdiction under the Legal
          Metrology (Packaged Commodities) Rules, 2011.
        </p>

        {/* A count is only shown once the register has answered; a zero before that is a claim. */}
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="shown"
          className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4"
        >
          {tiles.map((tile) => (
            <motion.div key={tile.label} variants={rise} className="card p-4 sm:p-5">
              <span className="block text-label text-mute">{tile.label}</span>
              <span className="mt-1 block font-display text-display text-ink">
                {loading ? (
                  <span className="skeleton block h-[1.05em] w-14" />
                ) : fetchError ? (
                  <span className="text-mute" aria-label="Not available">
                    —
                  </span>
                ) : (
                  <CountUp value={tile.value} />
                )}
              </span>
            </motion.div>
          ))}
        </motion.div>

        <section aria-label="Filters" className="card mt-6 flex flex-col gap-4 p-5 sm:p-6">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_280px]">
            <label className="flex flex-col gap-1.5">
              <span className="text-label text-mute">Search premise</span>
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name, district, or state..."
                className="input"
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-label text-mute">District jurisdiction</span>
              <select
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}
                className="input"
              >
                <option value="ALL">All districts</option>
                {districts.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div
              role="group"
              aria-label="Vendor premise type"
              className="isolate flex w-full gap-1 rounded-full bg-sunken p-1 sm:w-auto"
            >
              {TYPE_FILTERS.map((option) => {
                const active = vendorTypeFilter === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setVendorTypeFilter(option.value)}
                    className={`relative min-h-target flex-1 whitespace-nowrap rounded-full px-2.5 text-secondary sm:px-4 transition-colors duration-base ease-out ${
                      active ? 'font-medium text-ink' : 'text-mute hover:text-ink'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="vendor-type-pill"
                        transition={spring.snap}
                        className="absolute inset-0 -z-10 rounded-full bg-surface shadow-e1"
                      />
                    )}
                    {option.label}
                  </button>
                )
              })}
            </div>

            {filtersActive && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('')
                  setVendorTypeFilter('ALL')
                  setDistrictFilter('ALL')
                }}
                className="btn btn-ghost px-4"
              >
                Reset filters
              </button>
            )}
          </div>
        </section>

        {loading ? (
          <div className="mt-6" aria-busy="true" aria-label="Loading vendor register">
            <div className="skeleton h-4 w-48" />
            <div className="card mt-3 hidden overflow-hidden lg:block">
              <div className="h-[41px] border-b border-hairline" />
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-6 border-b border-hairline/70 px-5 py-4 last:border-b-0">
                  <div className="w-[30%] space-y-2">
                    <div className="skeleton h-5 w-3/4" />
                    <div className="skeleton h-3.5 w-1/2" />
                  </div>
                  <div className="w-[20%]">
                    <div className="skeleton h-6 w-24 rounded-full" />
                  </div>
                  <div className="skeleton h-5 w-[26%]" />
                  <div className="skeleton ml-auto h-4 w-32" />
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-3 lg:hidden">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="card p-5">
                  <div className="skeleton h-5 w-2/3" />
                  <div className="skeleton mt-2 h-6 w-24 rounded-full" />
                  <div className="skeleton mt-4 h-4 w-4/5" />
                  <div className="skeleton mt-2 h-3.5 w-1/2" />
                </div>
              ))}
            </div>
          </div>
        ) : fetchError ? (
          <div className="mt-6">
            <Notice role="alert" title="The vendor register did not load">
              {fetchError}
            </Notice>
          </div>
        ) : (
          <>
            <div className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
              <span className="font-mono text-label text-mute">
                Showing {filteredVendors.length} of {vendors.length} premises
              </span>
              <span className="text-label text-mute">
                Legal Metrology (Packaged Commodities) Rules, 2011
              </span>
            </div>

            {filteredVendors.length === 0 ? (
              <div className="mt-3">
                {vendors.length === 0 ? (
                  <Notice title="No vendor premises recorded in this jurisdiction." />
                ) : (
                  <Notice title="No premises match these filters.">
                    Clear the search or choose another premise type or district.
                  </Notice>
                )}
              </div>
            ) : (
              <div className="mt-3">
                <div className="card hidden overflow-hidden lg:block">
                  <table className="w-full border-collapse text-left">
                    <caption className="sr-only">
                      Registered vendor premises and statutory jurisdiction
                    </caption>
                    <thead>
                      <tr className="border-b border-hairline text-label text-mute">
                        <th scope="col" className="w-[30%] px-5 py-3 font-medium">
                          Vendor / premise
                        </th>
                        <th scope="col" className="w-[20%] px-5 py-3 font-medium">
                          Premise type
                        </th>
                        <th scope="col" className="w-[30%] px-5 py-3 font-medium">
                          Jurisdiction (district, state)
                        </th>
                        <th scope="col" className="w-[20%] px-5 py-3 text-right font-medium">
                          Registered at
                        </th>
                      </tr>
                    </thead>
                    <motion.tbody variants={stagger} initial="hidden" animate="shown">
                      {filteredVendors.map((vendor) => (
                        <motion.tr
                          key={vendor.id}
                          variants={rise}
                          className="border-b border-hairline/70 transition-colors duration-base ease-out last:border-b-0 hover:bg-focus-tint/40"
                        >
                          <td className="px-5 py-4 align-top">
                            <p className="text-body font-medium text-ink">{vendor.name}</p>
                            <p className="font-mono text-label text-mute [overflow-wrap:anywhere]">
                              {vendor.id}
                            </p>
                          </td>
                          <td className="px-5 py-4 align-top">
                            <TypeChip type={vendor.vendor_type} />
                          </td>
                          <td className="px-5 py-4 align-top">
                            <p className="text-body text-ink">{jurisdictionLine(vendor)}</p>
                          </td>
                          <td className="px-5 py-4 text-right align-top font-mono text-label text-mute">
                            {formatTimestamp(vendor.created_at)}
                          </td>
                        </motion.tr>
                      ))}
                    </motion.tbody>
                  </table>
                </div>

                <motion.div
                  variants={stagger}
                  initial="hidden"
                  animate="shown"
                  className="space-y-3 lg:hidden"
                >
                  {filteredVendors.map((vendor) => (
                    <motion.article key={vendor.id} variants={rise} className="card p-5">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <h2 className="min-w-0 font-sans text-body font-semibold text-ink">
                          {vendor.name}
                        </h2>
                        <TypeChip type={vendor.vendor_type} />
                      </div>
                      <p className="mt-3 text-secondary text-mute">
                        Jurisdiction: {jurisdictionLine(vendor)}
                      </p>
                      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-hairline/70 pt-3 font-mono text-label text-mute">
                        <span className="[overflow-wrap:anywhere]">{vendor.id}</span>
                        <span>{formatTimestamp(vendor.created_at)}</span>
                      </div>
                    </motion.article>
                  ))}
                </motion.div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
