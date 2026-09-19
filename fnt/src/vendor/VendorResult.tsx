import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { STATE_SENTENCE, VERDICT_SENTENCE, summariseByField } from '../consumer/plainLanguage'
import { FieldStateChip } from '../officer/components/FieldStateChip'
import { VerdictBanner } from '../officer/components/VerdictBanner'
import { serverMessage, thrownMessage } from '../services/errors'
import type { components } from '../services/generated/schema'
import { awaitScanOutcome } from '../services/scans'
import { vendorClient } from '../services/vendorClient'
import { rise, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { VendorHeader } from './VendorHeader'

type ScanDetail = components['schemas']['ScanDetail']
type RoutingDecision = components['schemas']['RoutingDecision']
type FieldState = components['schemas']['FieldState']

const STATE_SHORT: Record<FieldState, string> = {
  PASS: 'FOUND',
  FAIL: 'CHECK',
  REVIEW_REQUIRED: 'REVIEW',
  INSUFFICIENT_EVIDENCE: 'NOT READ',
  NOT_APPLICABLE: 'N/A',
}

const TIER_LABEL: Record<RoutingDecision['target_tier'], string> = {
  state: 'state tier',
  region: 'regional tier',
  district: 'district tier',
}

/** `GET /vendor/scans/{id}`, read until the status leaves PROCESSING. */
async function readVendorScan(scanId: string): Promise<ScanDetail | undefined> {
  const { data, error, response } = await vendorClient.GET('/vendor/scans/{scan_id}', {
    params: { path: { scan_id: scanId } },
  })
  if (error) throw new Error(serverMessage(error, response))
  return data?.scan
}

/**
 * The outcome of one self-check. What an officer's page has and this one does not: the
 * determination sheet and the category confirmation. Both are officer acts the server
 * refuses to a vendor token, so they are not drawn.
 */
export function VendorResult() {
  const { scanId = '' } = useParams()
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [routing, setRouting] = useState<RoutingDecision | null>(null)
  const [waited, setWaited] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    awaitScanOutcome(scanId, (s) => !cancelled && setWaited(s), readVendorScan)
      .then(async (d) => {
        if (cancelled) return
        setScan(d)
        // The routing decision is on the vendor view, not the scan; read it once evaluated.
        const { data } = await vendorClient.GET('/vendor/scans/{scan_id}', {
          params: { path: { scan_id: scanId } },
        })
        if (!cancelled) setRouting(data?.routing ?? null)
      })
      .catch((e: unknown) => !cancelled && setError(thrownMessage(e)))
    return () => {
      cancelled = true
    }
  }, [scanId])

  return (
    <div className="aurora">
      <VendorHeader title="Result" />
      <main className="mx-auto max-w-[720px] px-4 pb-16 pt-6 sm:pt-10">
        {error && (
          <Notice
            title="Could not read the result"
            role="alert"
            action={
              <Link to="/vendor" className="btn btn-quiet">
                Back to your submissions
              </Link>
            }
          >
            <span className="font-mono">{error}</span>
          </Notice>
        )}
        {!error && !scan && (
          <div className="rounded-card border-2 border-dotted border-mute bg-surface p-5 sm:p-7" aria-busy="true">
            <p className="font-display text-title">Reading the label…</p>
            <p className="mt-2 text-body text-mute">
              {waited < 5 ? 'Sent. Waiting for the server to read the panel.' : `Still reading, ${waited} s so far.`}
            </p>
          </div>
        )}
        {scan && <Outcome scan={scan} routing={routing} />}
      </main>
    </div>
  )
}

function Outcome({ scan, routing }: { scan: ScanDetail; routing: RoutingDecision | null }) {
  const fields = summariseByField(scan.findings)
  const unread = scan.findings.filter((f) => f.state === 'INSUFFICIENT_EVIDENCE').length
  return (
    <motion.div variants={stagger} initial="hidden" animate="shown" className="space-y-10">
      <section>
        {scan.verdict ? (
          <>
            <VerdictBanner verdict={scan.verdict} />
            <p className="mt-4 text-body">{VERDICT_SENTENCE[scan.verdict]}</p>
          </>
        ) : scan.quality ? (
          <div className="rounded-card border-2 border-dotted border-mute bg-surface p-5 sm:p-7">
            <p className="font-display text-title">Photograph not usable — no verdict</p>
            <p className="mt-2 text-body text-mute">{scan.quality.instruction}</p>
          </div>
        ) : (
          <div className="rounded-card border-2 border-dotted border-mute bg-surface p-5 sm:p-7">
            <p className="font-display text-title">No verdict — {scan.status}</p>
            <p className="mt-2 text-body text-mute">
              {scan.status === 'failed'
                ? 'Reading this photograph did not finish. Nothing was decided about the package.'
                : 'No verdict was issued for this photograph.'}
            </p>
          </div>
        )}
        <p className="mt-3 font-mono text-label text-mute">
          Scan {scan.id.slice(0, 8)} · rule set {scan.rule_set_version} · uncalibrated photograph, so no
          size in millimetres is reported
        </p>
      </section>

      {scan.verdict && (
        <motion.section variants={rise} className="rounded-card border-2 border-dotted border-mute bg-surface p-5">
          <p className="font-mono text-label font-semibold text-ink">WHAT THIS IS</p>
          <p className="mt-2 text-secondary text-mute">
            A self-check recommendation to you. Sector-specific rules (Rule 7, 8 and 9) stay at
            "not read" until a Legal Metrology officer confirms the product category, which only an
            officer can do. Nothing here is a finding of contravention.
          </p>
          {routing && (
            <p className="mt-2 font-mono text-label text-mute">
              Routed to the {TIER_LABEL[routing.target_tier]} for attention ·{' '}
              {routing.requires_visit ? 'a premises visit may follow' : 'no premises visit indicated'} ·{' '}
              {routing.action_required ? 'action on your part is indicated' : 'no action indicated'}
            </p>
          )}
          {unread > 0 && (
            <p className="mt-2 font-mono text-label text-mute">
              {unread} declaration{unread === 1 ? '' : 's'} could not be read from this photograph.
            </p>
          )}
        </motion.section>
      )}

      {fields.length > 0 && (
        <motion.section variants={rise}>
          <h2 className="text-section">What the rules ask for on the label</h2>
          <p className="mt-1 text-secondary text-mute">
            One line per declaration, with the rule that applies. "Not read" is a statement about
            the photograph, not about the package.
          </p>
          <motion.ul variants={stagger} className="card mt-4 divide-y divide-hairline/70 px-4 sm:px-5">
            {fields.map((f) => (
              <motion.li key={f.field} variants={rise} className="py-4">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                  <p className="text-body font-medium">{f.label}</p>
                  <FieldStateChip state={f.state} label={STATE_SHORT[f.state]} />
                </div>
                <p className="mt-1 text-secondary text-mute">{STATE_SENTENCE[f.state]}</p>
                {f.observed && f.state === 'PASS' && (
                  <p className="mt-2 break-words rounded-ctl bg-sunken/60 px-3 py-2 font-mono text-secondary text-ink">
                    Read as: {f.observed.length > 160 ? `${f.observed.slice(0, 160)}…` : f.observed}
                  </p>
                )}
                <p className="mt-2 font-mono text-label text-mute">{f.clauses.join(', ')}</p>
              </motion.li>
            ))}
          </motion.ul>
        </motion.section>
      )}

      <motion.p variants={rise}>
        <Link to="/vendor" className="btn btn-quiet">
          Check another package
        </Link>
      </motion.p>
    </motion.div>
  )
}
