import { VENDOR_SUBMISSIONS } from './vendor-submissions.fixture'

export type ComplaintStatus = 'RAISED' | 'ACKNOWLEDGED' | 'RESOLVED' | 'REJECTED'

export interface ComplaintRecord {
  id: string
  scan_id: string
  verdict_id: string
  manufacturer_name: string
  issue_summary: string
  status: ComplaintStatus
  raised_by_officer_id: string
  raised_by_officer_name: string
  raised_at: string
  supersedes_id: string | null
  event_note?: string
}

export interface ComplaintThread {
  thread_id: string
  latest_record: ComplaintRecord
  history: ComplaintRecord[]
  scan_id: string
  verdict_id: string
  manufacturer_name: string
  product_description: string
  vendor_name: string
  district: string
  state: string
}

export const INITIAL_COMPLAINTS: ComplaintRecord[] = [
  // Thread 1: RAISED -> ACKNOWLEDGED -> RESOLVED
  {
    id: 'cmp-1001-a1',
    scan_id: 'scn-9011-a1b2',
    verdict_id: 'vrd-7011-c3d4',
    manufacturer_name: 'Apex Agro Refining Private Limited',
    issue_summary: 'Net quantity declaration letter height measured at 1.9 mm, below mandatory 2.5 mm under Rule 7(2) Table-I.',
    status: 'RAISED',
    raised_by_officer_id: 'KLM-HYD-04',
    raised_by_officer_name: 'R. K. Sharma',
    raised_at: '2026-09-07T12:00:00+05:30',
    supersedes_id: null,
    event_note: 'Statutory escalation notice issued to registered manufacturing unit in Telangana.',
  },
  {
    id: 'cmp-1001-a2',
    scan_id: 'scn-9011-a1b2',
    verdict_id: 'vrd-7011-c3d4',
    manufacturer_name: 'Apex Agro Refining Private Limited',
    issue_summary: 'Net quantity declaration letter height measured at 1.9 mm, below mandatory 2.5 mm under Rule 7(2) Table-I.',
    status: 'ACKNOWLEDGED',
    raised_by_officer_id: 'KLM-HYD-04',
    raised_by_officer_name: 'R. K. Sharma',
    raised_at: '2026-09-07T14:30:00+05:30',
    supersedes_id: 'cmp-1001-a1',
    event_note: 'Manufacturer compliance division acknowledged notice receipt ref REG/LMO/2026/044.',
  },
  {
    id: 'cmp-1001-a3',
    scan_id: 'scn-9011-a1b2',
    verdict_id: 'vrd-7011-c3d4',
    manufacturer_name: 'Apex Agro Refining Private Limited',
    issue_summary: 'Net quantity declaration letter height measured at 1.9 mm, below mandatory 2.5 mm under Rule 7(2) Table-I.',
    status: 'RESOLVED',
    raised_by_officer_id: 'KLM-HYD-04',
    raised_by_officer_name: 'R. K. Sharma',
    raised_at: '2026-09-07T18:00:00+05:30',
    supersedes_id: 'cmp-1001-a2',
    event_note: 'Manufacturer submitted undertaking and rectified cylinder artwork ensuring 2.8 mm numeral height for subsequent production runs.',
  },

  // Thread 2: RAISED -> ACKNOWLEDGED (Awaiting resolution/rejection)
  {
    id: 'cmp-1002-b1',
    scan_id: 'scn-9012-e5f6',
    verdict_id: 'vrd-7012-g7h8',
    manufacturer_name: 'GlowCare Laboratories LLP',
    issue_summary: 'Mandatory consumer care address omitted email and contact telephone on cosmetic package under Rule 6(1)(da).',
    status: 'RAISED',
    raised_by_officer_id: 'KLM-MED-03',
    raised_by_officer_name: 'M. S. Reddy',
    raised_at: '2026-09-07T16:30:00+05:30',
    supersedes_id: null,
    event_note: 'Formal notice issued regarding absent consumer care telephone and email credentials.',
  },
  {
    id: 'cmp-1002-b2',
    scan_id: 'scn-9012-e5f6',
    verdict_id: 'vrd-7012-g7h8',
    manufacturer_name: 'GlowCare Laboratories LLP',
    issue_summary: 'Mandatory consumer care address omitted email and contact telephone on cosmetic package under Rule 6(1)(da).',
    status: 'ACKNOWLEDGED',
    raised_by_officer_id: 'KLM-MED-03',
    raised_by_officer_name: 'M. S. Reddy',
    raised_at: '2026-09-07T17:45:00+05:30',
    supersedes_id: 'cmp-1002-b1',
    event_note: 'Manufacturer legal team confirmed receipt. Technical explanation pending within 7 working days.',
  },

  // Thread 3: RAISED (Active, awaiting acknowledgement)
  {
    id: 'cmp-1003-c1',
    scan_id: 'scn-9018-c9d0',
    verdict_id: 'vrd-7018-e1f2',
    manufacturer_name: 'CleanStar Consumer Products Pvt Ltd',
    issue_summary: 'Retail sale price declaration omits "incl. of all taxes" words as mandated by Rule 6(1)(e).',
    status: 'RAISED',
    raised_by_officer_id: 'KLM-HYD-04',
    raised_by_officer_name: 'R. K. Sharma',
    raised_at: '2026-09-06T10:00:00+05:30',
    supersedes_id: null,
    event_note: 'Notice dispatched requesting explanation for omission of statutory tax inclusion wording.',
  },

  // Thread 4: RAISED -> ACKNOWLEDGED -> REJECTED
  {
    id: 'cmp-1004-d1',
    scan_id: 'scn-9014-m3n4',
    verdict_id: 'vrd-7014-o5p6',
    manufacturer_name: 'SpicyBite Foods India Ltd',
    issue_summary: 'Multi-piece package omitted mandatory statement of quantity for each individual piece under Rule 24.',
    status: 'RAISED',
    raised_by_officer_id: 'MH-PUN-01',
    raised_by_officer_name: 'V. S. Kulkarni',
    raised_at: '2026-09-05T11:00:00+05:30',
    supersedes_id: null,
    event_note: 'Escalation raised under Rule 24 requirements for multipack declarations.',
  },
  {
    id: 'cmp-1004-d2',
    scan_id: 'scn-9014-m3n4',
    verdict_id: 'vrd-7014-o5p6',
    manufacturer_name: 'SpicyBite Foods India Ltd',
    issue_summary: 'Multi-piece package omitted mandatory statement of quantity for each individual piece under Rule 24.',
    status: 'ACKNOWLEDGED',
    raised_by_officer_id: 'MH-PUN-01',
    raised_by_officer_name: 'V. S. Kulkarni',
    raised_at: '2026-09-05T13:00:00+05:30',
    supersedes_id: 'cmp-1004-d1',
    event_note: 'Manufacturer representative acknowledged notice via electronic portal.',
  },
  {
    id: 'cmp-1004-d3',
    scan_id: 'scn-9014-m3n4',
    verdict_id: 'vrd-7014-o5p6',
    manufacturer_name: 'SpicyBite Foods India Ltd',
    issue_summary: 'Multi-piece package omitted mandatory statement of quantity for each individual piece under Rule 24.',
    status: 'REJECTED',
    raised_by_officer_id: 'MH-PUN-01',
    raised_by_officer_name: 'V. S. Kulkarni',
    raised_at: '2026-09-06T14:20:00+05:30',
    supersedes_id: 'cmp-1004-d2',
    event_note: 'Manufacturer established each individual internal packet was separately weighed and carried independent declaration; complaint closed without enforcement action.',
  },
]

const STORAGE_KEY = 'pccs_officer_complaints_v1'

export function loadComplaintRecords(): ComplaintRecord[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as ComplaintRecord[]
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch {
    // Fall back to initial records if storage error
  }
  return [...INITIAL_COMPLAINTS]
}

export function saveComplaintRecords(records: ComplaintRecord[]): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(records))
  } catch {
    // Ignore storage quota issues
  }
}

/**
 * Builds threads from an append-only set of records.
 * A thread head is any record that is NOT superseded by another record.
 */
export function buildComplaintThreads(records: ComplaintRecord[]): ComplaintThread[] {
  const supersededIds = new Set<string>()
  for (const r of records) {
    if (r.supersedes_id) {
      supersededIds.add(r.supersedes_id)
    }
  }

  // The latest record in each active or closed thread is the one not superseded
  const heads = records.filter((r) => !supersededIds.has(r.id))

  return heads.map((head) => {
    // Reconstruct history chain from head back to root
    const history: ComplaintRecord[] = []
    let curr: ComplaintRecord | undefined = head
    while (curr) {
      history.unshift(curr)
      if (!curr.supersedes_id) break
      const parentId: string = curr.supersedes_id
      curr = records.find((r) => r.id === parentId)
    }

    const submission = VENDOR_SUBMISSIONS.find((s) => s.scan_id === head.scan_id)

    return {
      thread_id: history[0]?.id ?? head.id,
      latest_record: head,
      history,
      scan_id: head.scan_id,
      verdict_id: head.verdict_id,
      manufacturer_name: head.manufacturer_name,
      product_description: submission?.product_description ?? 'Packaged commodity',
      vendor_name: submission?.vendor.name ?? 'Retail premises',
      district: submission?.vendor.district ?? 'Local jurisdiction',
      state: submission?.vendor.state ?? 'State jurisdiction',
    }
  })
}

/**
 * UI Rule 1 Check:
 * A complaint can ONLY be raised from a verdict that an officer has explicitly confirmed.
 * The UI must strictly forbid and hide the "Raise Complaint" path for raw machine verdicts.
 */
export function checkCanRaiseComplaint(scan_id: string): {
  allowed: boolean
  reason: string
  submission?: (typeof VENDOR_SUBMISSIONS)[number]
} {
  const submission = VENDOR_SUBMISSIONS.find((s) => s.scan_id === scan_id)
  if (!submission) {
    return {
      allowed: false,
      reason: 'Scan reference not found in inspection repository.',
    }
  }

  if (!submission.officer_confirmation.is_confirmed) {
    return {
      allowed: false,
      reason:
        'Forbidden: Verdict has not been explicitly confirmed by an officer. Human confirmation is strictly required prior to raising a complaint.',
      submission,
    }
  }

  return {
    allowed: true,
    reason: 'Verdict has been confirmed by an officer.',
    submission,
  }
}
