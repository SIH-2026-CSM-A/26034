import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import type { BarcodeResult } from '../services/barcode'
import type { components } from '../services/generated/schema'
import { awaitScanOutcome, readConsumerScan } from '../services/scans'
import { FieldStateChip } from '../officer/components/FieldStateChip'
import { VerdictBanner } from '../officer/components/VerdictBanner'
import { rise, stagger } from '../ui/motion'
import { Notice } from '../ui/Notice'
import { ConsumerHeader } from './ConsumerHeader'
import { lookupAdditive } from './additives'
import { additiveCodes, ingredientText } from './ingredients'
import { STATE_SENTENCE, VERDICT_SENTENCE, summariseByField } from './plainLanguage'
import { ReviewsPanel } from './ReviewsPanel'

type ScanDetail = components['schemas']['ScanDetail']
type FieldState = components['schemas']['FieldState']

/** Plain words for a shopper. Drawn by FieldStateChip, so glyph, fill and border still carry the state. */
const STATE_SHORT: Record<FieldState, string> = {
  PASS: 'FOUND',
  FAIL: 'CHECK',
  REVIEW_REQUIRED: 'REVIEW',
  INSUFFICIENT_EVIDENCE: 'NOT READ',
  NOT_APPLICABLE: 'N/A',
}

export function ConsumerResult() {
  const { scanId = '' } = useParams()
  const location = useLocation()
  const barcode = (location.state as { barcode?: BarcodeResult | null } | null)?.barcode ?? null
  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [waited, setWaited] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    awaitScanOutcome(scanId, (s) => !cancelled && setWaited(s), readConsumerScan)
      .then((d) => !cancelled && setScan(d))
      .catch((e: unknown) =>
        !cancelled && setError(e instanceof Error ? e.message : 'Could not read the result.'),
      )
    return () => {
      cancelled = true
    }
  }, [scanId])

  return (
    <div className="aurora">
      <ConsumerHeader title="Result" />
      <main className="mx-auto max-w-[720px] px-4 pb-16 pt-6 sm:pt-10">
        {error && (
          <Notice
            title="Could not read the result"
            role="alert"
            action={
              <Link to="/consumer" className="btn btn-quiet">
                Try another photograph
              </Link>
            }
          >
            {error}
          </Notice>
        )}

        {!scan && !error && <Reading waited={waited} />}

        {scan && <Outcome scan={scan} barcode={barcode} />}
      </main>
    </div>
  )
}

/**
 * The wait, drawn in the shape of the result: a banner-sized block, then ledger rows.
 * When the outcome lands it replaces like for like and nothing jumps. The elapsed
 * seconds are the poller's own count, so the screen always says how long it has been.
 */
function Reading({ waited }: { waited: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-6">
      <div className="card p-5 sm:p-7">
        <div className="flex items-center gap-4">
          <span aria-hidden="true" className="relative flex h-11 w-11 shrink-0 items-center justify-center sm:h-14 sm:w-14">
            <span className="absolute inset-0 animate-ping rounded-full bg-accent/20 [animation-duration:1.8s]" />
            <span className="h-3 w-3 rounded-full bg-accent" />
          </span>
          <div className="min-w-0">
            <p className="font-display text-title">Reading the label</p>
            <p className="font-mono text-label text-mute">{waited > 0 ? `${waited}s so far` : 'Starting…'}</p>
          </div>
        </div>
        <p className="mt-3 text-secondary text-mute">
          The server is reading the text on your photograph and checking it against the
          rules. This usually takes under a minute.
        </p>
      </div>
      <div aria-hidden="true" className="card divide-y divide-hairline/70 px-5">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3 py-4">
            <span className="skeleton h-7 w-20 rounded-full" />
            <span className="flex-1 space-y-2">
              <span className="skeleton block h-4 w-2/5" />
              <span className="skeleton block h-3 w-4/5" />
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Outcome({ scan, barcode }: { scan: ScanDetail; barcode: BarcodeResult | null }) {
  const fields = summariseByField(scan.findings)
  const ingredients = ingredientText(scan.panel_spans)
  const codes = ingredients ? additiveCodes(ingredients) : []

  return (
    <motion.div variants={stagger} initial="hidden" animate="shown" className="space-y-10">
      {/* Not a staggered child: the verdict is on screen on the frame the data lands. */}
      <section>
        {scan.verdict ? (
          <>
            <VerdictBanner verdict={scan.verdict} />
            <p className="mt-4 text-body">{VERDICT_SENTENCE[scan.verdict]}</p>
          </>
        ) : scan.quality ? (
          // A rejected photograph says nothing about the package, so it wears no state colour.
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
          Scan {scan.id.slice(0, 8)} · rule set {scan.rule_set_version} · uncalibrated photograph,
          so no size in millimetres is reported
        </p>
      </section>

      {fields.length > 0 && (
        <motion.section variants={rise}>
          <h2 className="text-section">What the rules ask for on a label</h2>
          <p className="mt-1 text-secondary text-mute">
            One line per declaration, with the rule that applies. "Not read" is a statement
            about the photograph, not about the package.
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
                <p className="mt-2 font-mono text-label text-mute">
                  {f.clauses.join(', ')}
                  {f.unassessedClauses.length > 0 &&
                    ` · ${f.unassessedClauses.length} further rule${f.unassessedClauses.length === 1 ? '' : 's'} not assessable from this photograph`}
                </p>
              </motion.li>
            ))}
          </motion.ul>
        </motion.section>
      )}

      <motion.section variants={rise}>
        <h2 className="text-section">Ingredients as declared on the label</h2>
        {ingredients ? (
          <>
            <p className="card mt-3 whitespace-pre-wrap break-words p-4 font-mono text-secondary">
              {ingredients}
            </p>
            <p className="mt-2 text-label text-mute">
              Exactly as read from the photograph, in the label's own words. Not corrected, not
              interpreted.
            </p>
          </>
        ) : (
          <p className="mt-2 text-secondary text-mute">
            No line beginning "Ingredients" was read on this photograph. Many products, and
            every non-food product, carry none.
          </p>
        )}
      </motion.section>

      <motion.section variants={rise}>
        <h2 className="text-section">Additive codes in that declaration</h2>
        <p className="mt-1 text-secondary text-mute">
          Each code is matched against a reference sourced from the FSS regulations. The
          entry says what the code is and what the regulation requires be declared. It
          makes no safety judgement of its own.
        </p>
        {codes.length === 0 ? (
          <p className="mt-3 text-secondary text-mute">No INS or E additive codes found in the declaration.</p>
        ) : (
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {codes.map((code) => {
              const entry = lookupAdditive(code)
              return (
                <li key={code} className="card p-4">
                  <p className="font-mono text-label text-mute">INS {code}</p>
                  {entry ? (
                    <>
                      <p className="mt-0.5 text-body font-medium">{entry.name}</p>
                      <p className="text-secondary text-mute">{entry.functionalClass}</p>
                      <p className="mt-2 text-secondary">
                        {entry.declaration
                          ? entry.declaration.requirement
                          : 'No specific declaration requirement identified.'}
                      </p>
                      <p className="mt-2 font-mono text-label text-mute">
                        {entry.declaration ? entry.declaration.citation : entry.citation}
                      </p>
                      <p className="font-mono text-label text-mute">Name and class: {entry.citation}</p>
                    </>
                  ) : (
                    <p className="mt-1 text-secondary text-mute">Not assessed — this code is not in the sourced reference.</p>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </motion.section>

      <motion.section variants={rise}>
        <h2 className="text-section">Barcode</h2>
        {barcode ? (
          <p className="mt-2 break-all font-mono text-body">
            {barcode.value} <span className="text-mute">· {barcode.symbology}</span>
            {!barcode.checkDigitVerifies && (
              <span className="text-mute"> · check digit does not verify</span>
            )}
          </p>
        ) : (
          <p className="mt-2 text-secondary text-mute">No barcode was read from this photograph.</p>
        )}
        <p className="mt-1 text-label text-mute">
          Read in your browser from the photograph. The digits are shown as printed; nothing
          is looked up against any registry and no product name is inferred from them.
        </p>
      </motion.section>

      <motion.div variants={rise}>
        <ReviewsPanel initialIdentifier={barcode?.value ?? ''} />
      </motion.div>

      <motion.div variants={rise}>
        <Link to="/consumer" className="btn btn-primary w-full py-4 text-body">
          Check another label
        </Link>
      </motion.div>
    </motion.div>
  )
}
