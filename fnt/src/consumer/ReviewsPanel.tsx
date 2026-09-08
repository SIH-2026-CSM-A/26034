import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'

type Consensus = components['schemas']['PublishedConsensus']
type Claim = components['schemas']['ConsumerSafetyClaim']

/**
 * Identifiers whose reviews include submissions seeded for the demonstration. They are
 * labelled as such wherever they appear; nothing seeded is presented as field-collected.
 */
export const SEEDED_DEMO_IDENTIFIERS: ReadonlySet<string> = new Set([
  '8901719100015',
  '8901725113320',
])

/**
 * Anonymous safe / unsafe sentiment for a product identifier, typically its barcode.
 * Shows only what the server has published: a sentiment becomes visible once enough
 * independent submissions agree on it, a deterministic threshold set in configuration.
 */
export function ReviewsPanel({ initialIdentifier = '' }: { initialIdentifier?: string }) {
  const [identifier, setIdentifier] = useState(initialIdentifier)
  const [queried, setQueried] = useState<string | null>(null)
  const [consensus, setConsensus] = useState<Consensus[] | null>(null)
  const [submitted, setSubmitted] = useState<'PUBLISHED' | 'HELD' | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (id: string) => {
    const trimmed = id.trim()
    if (!trimmed) return
    setBusy(true)
    setError(null)
    try {
      const { data, error: apiError } = await apiClient.GET('/reviews/{product_identifier}', {
        params: { path: { product_identifier: trimmed } },
      })
      if (apiError || !data) {
        setError('Could not read reviews for that identifier.')
        return
      }
      setQueried(trimmed)
      setConsensus(data.published_consensus)
    } catch {
      setError('Could not read reviews for that identifier.')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    if (initialIdentifier) {
      setIdentifier(initialIdentifier)
      void load(initialIdentifier)
    }
  }, [initialIdentifier, load])

  const submit = useCallback(
    async (claim: Claim) => {
      const trimmed = identifier.trim()
      if (!trimmed) return
      setBusy(true)
      setError(null)
      try {
        const { data, error: apiError } = await apiClient.POST('/reviews', {
          body: { product_identifier: trimmed, consumer_safety_claim: claim },
        })
        if (apiError || !data) {
          setError('Your submission was not recorded.')
          return
        }
        setSubmitted(data.publication_status)
        await load(trimmed)
      } catch {
        setError('Your submission was not recorded.')
      } finally {
        setBusy(false)
      }
    },
    [identifier, load],
  )

  const seeded = queried !== null && SEEDED_DEMO_IDENTIFIERS.has(queried)

  return (
    <section>
      <h2 className="text-section font-semibold">What other shoppers reported</h2>
      <p className="mt-1 text-secondary text-mute">
        Anonymous. Each report is one word, safe or unsafe, against a product identifier —
        the barcode digits, if the pack has one. A sentiment is published automatically
        once at least 3 independent submissions agree; below that it stays unpublished. The
        threshold is a configurable prototype value and the rule is deterministic counting,
        nothing more.
      </p>

      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault()
          void load(identifier)
        }}
      >
        <label htmlFor="product-identifier" className="sr-only">
          Product identifier
        </label>
        <input
          id="product-identifier"
          inputMode="numeric"
          placeholder="Barcode digits, e.g. 8901719100015"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          className="min-h-target flex-1 border border-hairline bg-paper px-3 py-2 font-mono text-body"
        />
        <button
          type="submit"
          disabled={busy || !identifier.trim()}
          className="min-h-target border border-ink bg-paper px-4 py-2 font-mono text-label text-ink hover:bg-mute/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Look up
        </button>
      </form>

      {error && <p className="mt-2 text-secondary text-seal">{error}</p>}

      {queried !== null && consensus !== null && (
        <div className="mt-4 border border-hairline p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-mono text-label text-mute">Identifier {queried}</p>
            {seeded && (
              <span className="border border-query px-1.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-query">
                includes seeded demo records
              </span>
            )}
          </div>
          {consensus.length === 0 ? (
            <p className="mt-2 text-body">
              Nothing published yet for this identifier. Either no one has reported it, or
              fewer than 3 submissions agree so far.
            </p>
          ) : (
            <ul className="mt-2 space-y-1">
              {consensus.map((c) => (
                <li key={c.consumer_safety_claim} className="flex items-baseline gap-3">
                  <span
                    className={`border px-2 py-0.5 font-mono text-label font-semibold uppercase ${
                      c.consumer_safety_claim === 'safe' ? 'border-attest text-attest' : 'border-seal text-seal'
                    }`}
                  >
                    {c.consumer_safety_claim}
                  </span>
                  <span className="text-body">
                    {c.submission_count} shopper{c.submission_count === 1 ? '' : 's'} reported this
                  </span>
                </li>
              ))}
            </ul>
          )}
          {seeded && (
            <p className="mt-2 text-label text-mute">
              Seeded demo record: submissions for this identifier were entered to demonstrate
              the threshold, not collected in the field.
            </p>
          )}
        </div>
      )}

      {queried !== null && (
        <div className="mt-4">
          <p className="text-body font-medium">Add your own report for {queried}</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => submit('safe')}
              className="min-h-target flex-1 border-2 border-attest bg-paper px-4 py-2 font-mono text-label font-semibold text-attest hover:bg-attest/10 disabled:opacity-50"
            >
              SAFE
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => submit('unsafe')}
              className="min-h-target flex-1 border-2 border-seal bg-paper px-4 py-2 font-mono text-label font-semibold text-seal hover:bg-seal/10 disabled:opacity-50"
            >
              UNSAFE
            </button>
          </div>
          {submitted && (
            <p className="mt-2 text-secondary text-mute">
              Recorded.{' '}
              {submitted === 'PUBLISHED'
                ? 'Enough submissions agree, so this sentiment is published.'
                : 'Held unpublished until enough independent submissions agree.'}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
