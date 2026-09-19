/**
 * The reference objects the backend's `detect_reference_object` recognises, by the exact value
 * it matches on, with the physical dimension it scales from (its `REF_DIMS`). The label tells an
 * officer what to put in frame. Any other value is refused, and the scan is then evaluated
 * uncalibrated — which is how both officer forms shipped sending `coin` and `card`.
 */
export type ReferenceType = 'coin_10' | 'id_card' | 'ean_13'

export const REFERENCE_OBJECTS: ReadonlyArray<{ value: ReferenceType; label: string }> = [
  { value: 'coin_10', label: '₹10 coin — 27.0 mm diameter' },
  { value: 'id_card', label: 'ID-1 card (PAN, debit or credit card) — 85.60 × 53.98 mm' },
  { value: 'ean_13', label: 'EAN-13 barcode — 37.29 mm wide' },
]
