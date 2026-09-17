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
      <h2 className="text-section">What other shoppers reported</h2>
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
          placeholder="Barcode digits"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          className="input flex-1 font-mono"
        />
        <button
          type="submit"
          disabled={busy || !identifier.trim()}
          className="btn btn-quiet"
        >
          Look up
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-2 text-secondary font-medium text-ink">
          {error}
        </p>
      )}

      {queried !== null && consensus !== null && (
        <div className="card mt-4 p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-mono text-label text-mute">Identifier {queried}</p>
            {seeded && (
              <span className="badge-seeded">includes seeded demo records</span>
            )}
          </div>
          {consensus.length === 0 ? (
            <p className="mt-2 text-body">
              Nothing published yet for this identifier. Either no one has reported it, or
              fewer than 3 submissions agree so far.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {consensus.map((c) => (
                <li key={c.consumer_safety_claim} className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-ink/30 px-2.5 py-0.5 font-mono text-label font-semibold uppercase text-ink">
                    <ClaimIcon claim={c.consumer_safety_claim} />
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
              className="btn btn-quiet flex-1 font-mono font-semibold"
            >
              <ClaimIcon claim="safe" />
              SAFE
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => submit('unsafe')}
              className="btn btn-quiet flex-1 font-mono font-semibold"
            >
              <ClaimIcon claim="unsafe" />
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

/**
 * A shopper's opinion is not a finding, so it borrows neither PASS green nor the
 * rule-failure red. Thumb up, thumb down, and the word.
 */
function ClaimIcon({ claim }: { claim: Claim }) {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden="true"
      className={`h-4 w-4 shrink-0 ${claim === 'safe' ? '' : 'rotate-180'}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
    >
      <path d="M5 7.2 7.6 2c1 0 1.7.8 1.5 1.8L8.7 6h3.5c.8 0 1.4.8 1.2 1.6l-1 4.4c-.1.6-.6 1-1.2 1H5V7.2ZM2.5 7.2H5V13H2.5z" />
    </svg>
  )
}
