/**
 * Fixture: forty inspections awaiting review. Not live data — see README.md in
 * this directory.
 *
 * Forty because that is what a working day's queue looks like, and a queue
 * screen that only ever holds six rows never gets designed for the real job.
 *
 * Rows describe commodity types and never a brand or a manufacturer. A
 * fabricated brand name sitting in a compliance queue reads as a real finding
 * against a real company, which is not something a fixture may look like.
 */

import { Verdict } from './contracts'

export interface QueueRow {
  subject_ref: string
  verdict: Verdict
  /**
   * Lowest reading confidence across the record's findings — the weakest link,
   * since that is what decides whether the record can be relied on. `null`
   * where no finding cited a span, and the machine therefore makes no claim.
   */
  confidence: number | null
  /** Commodity type as declared. Never a brand. */
  product: string
  /** Net quantity as declared on the package. */
  declared_quantity: string
  /** ISO 8601 with offset, as the API emits it. */
  captured_at: string
  /** Count of findings not in PASS or NOT_APPLICABLE. */
  open_findings: number
}

export const queueRows: readonly QueueRow[] = [
  { subject_ref: 'SCAN-2026-0914-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.79, product: 'Biscuits', declared_quantity: '250 g', captured_at: '2026-09-06T09:11:48+05:30', open_findings: 4 },
  { subject_ref: 'SCAN-2026-0913-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.71, product: 'Refined sunflower oil', declared_quantity: '1 L', captured_at: '2026-09-06T08:52:10+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0912-FIXTURE', verdict: Verdict.PASS, confidence: 0.96, product: 'Iodised salt', declared_quantity: '1 kg', captured_at: '2026-09-06T08:40:55+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0911-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.88, product: 'Toilet soap', declared_quantity: '100 g', captured_at: '2026-09-06T08:22:31+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0910-FIXTURE', verdict: Verdict.REVIEW, confidence: null, product: 'Packaged drinking water', declared_quantity: '500 ml', captured_at: '2026-09-06T08:05:19+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0909-FIXTURE', verdict: Verdict.PASS, confidence: 0.93, product: 'Wheat flour', declared_quantity: '5 kg', captured_at: '2026-09-05T17:48:02+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0908-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.82, product: 'Instant noodles', declared_quantity: '70 g', captured_at: '2026-09-05T17:12:44+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0907-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.68, product: 'Hair oil', declared_quantity: '200 ml', captured_at: '2026-09-05T16:55:27+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0906-FIXTURE', verdict: Verdict.PASS, confidence: 0.98, product: 'Basmati rice', declared_quantity: '5 kg', captured_at: '2026-09-05T16:30:03+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0905-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.74, product: 'Detergent powder', declared_quantity: '1 kg', captured_at: '2026-09-05T15:58:41+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0904-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.91, product: 'Tea leaves', declared_quantity: '250 g', captured_at: '2026-09-05T15:20:16+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0903-FIXTURE', verdict: Verdict.PASS, confidence: 0.95, product: 'Ground coffee', declared_quantity: '200 g', captured_at: '2026-09-05T14:47:52+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0902-FIXTURE', verdict: Verdict.REVIEW, confidence: null, product: 'Shampoo', declared_quantity: '340 ml', captured_at: '2026-09-05T14:11:29+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0901-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.86, product: 'Mustard oil', declared_quantity: '500 ml', captured_at: '2026-09-05T13:38:07+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0900-FIXTURE', verdict: Verdict.PASS, confidence: 0.92, product: 'Toor dal', declared_quantity: '1 kg', captured_at: '2026-09-05T12:59:44+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0899-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.77, product: 'Biscuits', declared_quantity: '120 g', captured_at: '2026-09-05T12:20:35+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0898-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.84, product: 'Talcum powder', declared_quantity: '100 g', captured_at: '2026-09-05T11:44:18+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0897-FIXTURE', verdict: Verdict.PASS, confidence: 0.97, product: 'Refined groundnut oil', declared_quantity: '1 L', captured_at: '2026-09-05T11:09:56+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0896-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.70, product: 'Chilli powder', declared_quantity: '100 g', captured_at: '2026-09-05T10:31:22+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0895-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.89, product: 'Milk powder', declared_quantity: '400 g', captured_at: '2026-09-05T09:58:40+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0894-FIXTURE', verdict: Verdict.PASS, confidence: 0.94, product: 'Sugar', declared_quantity: '1 kg', captured_at: '2026-09-04T18:14:11+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0893-FIXTURE', verdict: Verdict.REVIEW, confidence: null, product: 'Face cream', declared_quantity: '50 g', captured_at: '2026-09-04T17:39:48+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0892-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.81, product: 'Ghee', declared_quantity: '500 ml', captured_at: '2026-09-04T17:02:25+05:30', open_findings: 4 },
  { subject_ref: 'SCAN-2026-0891-FIXTURE', verdict: Verdict.PASS, confidence: 0.99, product: 'Besan', declared_quantity: '500 g', captured_at: '2026-09-04T16:28:03+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0890-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.73, product: 'Toothpaste', declared_quantity: '150 g', captured_at: '2026-09-04T15:51:37+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0889-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.87, product: 'Fruit juice', declared_quantity: '1 L', captured_at: '2026-09-04T15:14:59+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0888-FIXTURE', verdict: Verdict.PASS, confidence: 0.91, product: 'Rava', declared_quantity: '1 kg', captured_at: '2026-09-04T14:40:16+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0887-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.66, product: 'Coconut oil', declared_quantity: '200 ml', captured_at: '2026-09-04T14:03:44+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0886-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.90, product: 'Namkeen', declared_quantity: '150 g', captured_at: '2026-09-04T13:27:21+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0885-FIXTURE', verdict: Verdict.PASS, confidence: 0.96, product: 'Poha', declared_quantity: '500 g', captured_at: '2026-09-04T12:49:08+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0884-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.75, product: 'Dish wash bar', declared_quantity: '200 g', captured_at: '2026-09-04T12:10:52+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0883-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.83, product: 'Turmeric powder', declared_quantity: '200 g', captured_at: '2026-09-04T11:33:30+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0882-FIXTURE', verdict: Verdict.PASS, confidence: 0.93, product: 'Moong dal', declared_quantity: '1 kg', captured_at: '2026-09-04T10:56:14+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0881-FIXTURE', verdict: Verdict.REVIEW, confidence: null, product: 'Body lotion', declared_quantity: '250 ml', captured_at: '2026-09-04T10:18:47+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0880-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.85, product: 'Cooking paste', declared_quantity: '100 g', captured_at: '2026-09-03T18:02:29+05:30', open_findings: 2 },
  { subject_ref: 'SCAN-2026-0879-FIXTURE', verdict: Verdict.PASS, confidence: 0.98, product: 'Jaggery', declared_quantity: '1 kg', captured_at: '2026-09-03T17:24:05+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0878-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.72, product: 'Incense sticks', declared_quantity: '100 N', captured_at: '2026-09-03T16:47:41+05:30', open_findings: 1 },
  { subject_ref: 'SCAN-2026-0877-FIXTURE', verdict: Verdict.POTENTIAL_VIOLATION, confidence: 0.80, product: 'Pickle', declared_quantity: '400 g', captured_at: '2026-09-03T16:09:18+05:30', open_findings: 3 },
  { subject_ref: 'SCAN-2026-0876-FIXTURE', verdict: Verdict.PASS, confidence: 0.95, product: 'Vermicelli', declared_quantity: '400 g', captured_at: '2026-09-03T15:31:56+05:30', open_findings: 0 },
  { subject_ref: 'SCAN-2026-0875-FIXTURE', verdict: Verdict.REVIEW, confidence: 0.69, product: 'Floor cleaner', declared_quantity: '500 ml', captured_at: '2026-09-03T14:54:33+05:30', open_findings: 2 },
]
