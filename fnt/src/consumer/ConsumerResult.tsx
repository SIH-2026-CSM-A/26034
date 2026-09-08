import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { components } from '../services/generated/schema'
import { awaitScanOutcome, readConsumerScan } from '../services/scans'
import { VerdictBanner } from '../officer/components/VerdictBanner'
import type { Verdict as FixtureVerdict } from '../fixtures/contracts'
import { ConsumerHeader } from './ConsumerHeader'
import { lookupAdditive } from './additives'
import { additiveCodes, ingredientText } from './ingredients'
import { STATE_SENTENCE, VERDICT_SENTENCE, summariseByField } from './plainLanguage'
import { ReviewsPanel } from './ReviewsPanel'

type ScanDetail = components['schemas']['ScanDetail']

const STATE_TONE: Record<string, string> = {
  PASS: 'border-attest text-attest',
  FAIL: 'border-seal text-seal',
  REVIEW_REQUIRED: 'border-query text-query',
  INSUFFICIENT_EVIDENCE: 'border-hairline text-mute',
  NOT_APPLICABLE: 'border-hairline text-mute',
}

const STATE_SHORT: Record<string, string> = {
  PASS: 'FOUND',
  FAIL: 'CHECK',
  REVIEW_REQUIRED: 'REVIEW',
  INSUFFICIENT_EVIDENCE: 'NOT READ',
  NOT_APPLICABLE: 'N/A',
}

export function ConsumerResult() {
  const { scanId = '' } = useParams()
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
    <div className="min-h-screen bg-paper text-ink">
      <ConsumerHeader title="Result" />
      <main className="mx-auto max-w-[720px] px-4 py-6 sm:py-10">
        {error && (
          <div className="border border-seal bg-paper p-4">
            <p className="text-body font-semibold text-seal">Could not read the result</p>
            <p className="mt-1 text-secondary text-mute">{error}</p>
            <Link to="/consumer" className="mt-3 inline-flex min-h-target items-center border border-ink px-4 py-2 text-label">
              Try another photograph
            </Link>
          </div>
        )}

        {!scan && !error && (
          <div className="border border-dashed border-mute p-6" role="status" aria-live="polite">
            <p className="font-mono text-label uppercase tracking-wide text-mute">Reading the label</p>
            <p className="mt-2 text-body">
              The server is reading the text on your photograph and checking it against the
              rules. This usually takes under a minute.
            </p>
            <p className="mt-2 font-mono text-secondary text-mute">
              {waited > 0 ? `${waited}s so far` : 'Starting…'}
            </p>
          </div>
        )}

        {scan && <Outcome scan={scan} />}
      </main>
    </div>
  )
}

function Outcome({ scan }: { scan: ScanDetail }) {
  const fields = summariseByField(scan.findings)
  const ingredients = ingredientText(scan.panel_spans)
  const codes = ingredients ? additiveCodes(ingredients) : []

  return (
    <div className="space-y-8">
      <section>
        {scan.verdict ? (
          <>
            <VerdictBanner verdict={scan.verdict as FixtureVerdict} />
            <p className="mt-3 text-body">{VERDICT_SENTENCE[scan.verdict]}</p>
          </>
        ) : scan.quality ? (
          <div className="border-y-2 border-seal py-5">
            <p className="font-mono text-label uppercase tracking-wide text-seal">
              Photograph not usable — no verdict
            </p>
            <p className="mt-2 text-body">{scan.quality.instruction}</p>
          </div>
        ) : (
          <div className="border-y-2 border-dashed border-mute py-5">
            <p className="font-mono text-label uppercase tracking-wide text-mute">
              No verdict — {scan.status}
            </p>
            <p className="mt-2 text-body">
              {scan.status === 'failed'
                ? 'Reading this photograph did not finish. Nothing was decided about the package.'
                : 'No verdict was issued for this photograph.'}
            </p>
          </div>
        )}
        <p className="mt-2 font-mono text-label text-mute">
          Scan {scan.id.slice(0, 8)} · rule set {scan.rule_set_version} · uncalibrated photograph,
          so no size in millimetres is reported
        </p>
      </section>

      {fields.length > 0 && (
        <section>
          <h2 className="text-section font-semibold">What the rules ask for on a label</h2>
          <p className="mt-1 text-secondary text-mute">
            One line per declaration, with the rule that applies. "Not read" is a statement
            about the photograph, not about the package.
          </p>
          <ul className="mt-4 divide-y divide-hairline border-y border-hairline">
            {fields.map((f) => (
              <li key={f.field} className="flex gap-3 py-3">
                <span
                  className={`mt-0.5 h-fit shrink-0 border px-1.5 py-0.5 font-mono text-[11px] font-semibold tracking-wide ${STATE_TONE[f.state]}`}
                >
                  {STATE_SHORT[f.state]}
                </span>
                <div className="min-w-0">
                  <p className="text-body font-medium">{f.label}</p>
                  <p className="text-secondary text-mute">{STATE_SENTENCE[f.state]}</p>
                  {f.observed && f.state === 'PASS' && (
                    <p className="mt-1 break-words font-mono text-secondary text-ink">
                      Read as: {f.observed.length > 160 ? `${f.observed.slice(0, 160)}…` : f.observed}
                    </p>
                  )}
                  <p className="mt-1 font-mono text-label text-mute">
                    {f.clauses.join(', ')}
                    {f.unassessedClauses.length > 0 &&
                      ` · ${f.unassessedClauses.length} further rule${f.unassessedClauses.length === 1 ? '' : 's'} not assessable from this photograph`}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="text-section font-semibold">Ingredients as declared on the label</h2>
        {ingredients ? (
          <>
            <p className="mt-2 whitespace-pre-wrap break-words border border-hairline bg-paper p-3 font-mono text-secondary">
              {ingredients}
            </p>
            <p className="mt-1 text-label text-mute">
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
      </section>

      <section>
        <h2 className="text-section font-semibold">Additive codes in that declaration</h2>
        <p className="mt-1 text-secondary text-mute">
          Each code is matched against a reference sourced from the FSS regulations. The
          entry says what the code is and what the regulation requires be declared. It
          makes no safety judgement of its own.
        </p>
        {codes.length === 0 ? (
          <p className="mt-3 text-secondary text-mute">No INS or E additive codes found in the declaration.</p>
        ) : (
          <ul className="mt-3 space-y-3">
            {codes.map((code) => {
              const entry = lookupAdditive(code)
              return (
                <li key={code} className="border border-hairline p-3">
                  <p className="font-mono text-body font-semibold">INS {code}</p>
                  {entry ? (
                    <>
                      <p className="text-body">{entry.name}</p>
                      <p className="text-secondary text-mute">{entry.functionalClass}</p>
                      <p className="mt-2 text-secondary">
                        {entry.declaration
                          ? entry.declaration.requirement
                          : 'No specific declaration requirement identified.'}
                      </p>
                      <p className="mt-1 font-mono text-label text-mute">
                        {entry.declaration ? entry.declaration.citation : entry.citation}
                      </p>
                      <p className="font-mono text-label text-mute">Name and class: {entry.citation}</p>
                    </>
                  ) : (
                    <p className="text-secondary text-mute">Not assessed — this code is not in the sourced reference.</p>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <ReviewsPanel />

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          to="/consumer"
          className="flex min-h-target flex-1 items-center justify-center border-2 border-ink bg-ink px-4 py-3 font-mono text-body text-paper hover:bg-ink/90"
        >
          Check another label
        </Link>
      </div>
    </div>
  )
}
