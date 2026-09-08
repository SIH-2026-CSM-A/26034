import { apiClient } from './apiClient'
import type { components } from './generated/schema'

type ScanDetail = components['schemas']['ScanDetail']

// How often to read the scan back while the server evaluates it. Evaluation is an OCR
// run of the better part of a minute on CPU; each read is a short request, which is the
// point — a single request that sits silent for that long does not survive a phone on a
// mobile network.
const POLL_INTERVAL_MS = 2000

// ponytail: ten minutes is a ceiling, not an estimate. Evaluation is serialised on the
// server, so a scan queued behind others waits for them first.
const POLL_DEADLINE_MS = 10 * 60 * 1000

/**
 * Read a scan back until its status leaves PROCESSING.
 *
 * Resolves with the finished detail: COMPLETE with a verdict, FAILED with none, or
 * RECEIVED with the capture instruction that replaced evaluation. Rejects if a read
 * fails or the deadline passes, and `onTick` reports elapsed seconds so a screen can
 * say that it is still waiting rather than looking stuck.
 */
export async function awaitScanOutcome(
  scanId: string,
  onTick?: (elapsedSeconds: number) => void,
): Promise<ScanDetail> {
  const started = Date.now()
  for (;;) {
    const { data, error } = await apiClient.GET('/scans/{scan_id}', {
      params: { path: { scan_id: scanId } },
    })
    if (error || !data) {
      throw new Error('Failed to fetch')
    }
    if (data.status !== 'processing') {
      return data
    }
    const elapsed = Date.now() - started
    if (elapsed > POLL_DEADLINE_MS) {
      throw new Error('Evaluation is still running on the server. Open the review ledger later.')
    }
    onTick?.(Math.round(elapsed / 1000))
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
  }
}
