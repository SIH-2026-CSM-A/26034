import { useEffect, useState } from 'react'
import { apiClient } from '../../services/apiClient'
import { serverMessage, thrownMessage } from '../../services/errors'
import { Notice } from '../../ui/Notice'

interface Issued {
  sha256: string
  url: string
  filename: string
}

async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

/**
 * `POST /scans/{scan_id}/evidence/report`: issues the filed PDF report. The server appends
 * the export's SHA-256 to the scan's evidence chain; this hashes the same bytes it
 * returned, so the digest shown is the one the chain records. The server refuses (409)
 * until an officer has finalised the review, and says so.
 */
export function EvidenceReport({ scanId, finalised }: { scanId: string; finalised: boolean }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [issued, setIssued] = useState<Issued | null>(null)

  useEffect(() => () => {
    if (issued) URL.revokeObjectURL(issued.url)
  }, [issued])

  async function generate() {
    setBusy(true)
    setError(null)
    try {
      const { data, error: apiError, response } = await apiClient.POST('/scans/{scan_id}/evidence/report', {
        params: { path: { scan_id: scanId }, query: { format: 'pdf' } },
        parseAs: 'blob',
      })
      if (data instanceof Blob) {
        setIssued({
          sha256: await sha256Hex(data),
          url: URL.createObjectURL(data),
          filename: `clausecam-report-${scanId.slice(0, 8)}.pdf`,
        })
        return
      }
      setError(serverMessage(apiError, response))
    } catch (err) {
      setError(thrownMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="evidence-report" className="card mt-8 p-5">
      <h2 id="evidence-report" className="text-section">
        Evidence report
      </h2>
      <p className="mt-1 text-secondary text-mute">
        {finalised
          ? 'Issue the filed report for this inspection. Its SHA-256 is appended to the evidence chain as the export record.'
          : 'Available once an officer has finalised the review of this inspection.'}
      </p>

      {error && (
        <div className="mt-4">
          <Notice title="Report refused" role="alert">
            <span className="font-mono">{error}</span>
          </Notice>
        </div>
      )}

      {issued && (
        <div className="mt-4 rounded-card bg-sunken p-4">
          <p className="text-label font-medium text-mute">SHA-256</p>
          <p className="mt-1 break-all font-mono text-secondary" data-testid="report-sha256">
            {issued.sha256}
          </p>
          <a href={issued.url} download={issued.filename} className="btn btn-quiet mt-3 text-secondary">
            Download {issued.filename}
          </a>
        </div>
      )}

      <button
        type="button"
        onClick={generate}
        disabled={!finalised || busy}
        className="btn btn-primary mt-4 text-body"
      >
        {busy ? 'Generating…' : issued ? 'Generate again' : 'Generate evidence report'}
      </button>
    </section>
  )
}
