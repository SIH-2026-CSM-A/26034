import { Verdict } from './contracts'

export type VendorType = 'godown' | 'supermarket' | 'kirana'

export interface Vendor {
  id: string
  name: string
  vendor_type: VendorType
  state: string
  region: string | null
  district: string | null
  address: string
  created_at: string
}

export interface RoutedOfficer {
  officer_id: string
  name: string
  designation: string
  jurisdiction_level: 'district' | 'region' | 'state'
  jurisdiction: string
}

export interface OfficerConfirmation {
  is_confirmed: boolean
  action: 'confirm' | 'reject' | 'override' | null
  officer_id: string | null
  confirmed_verdict: Verdict | null
  confirmed_at: string | null
  notes: string | null
}

export interface VendorSubmissionItem {
  scan_id: string
  verdict_id: string
  vendor: Vendor
  product_description: string
  product_category: 'food' | 'cosmetics' | 'medical_device'
  source_type: 'physical_label' | 'catalogue_record'
  captured_at: string
  recommended_verdict: Verdict
  routed_officer: RoutedOfficer
  officer_confirmation: OfficerConfirmation
  manufacturer_name: string
  issue_summary: string
  finding_counts: {
    pass: number
    review_required: number
    fail: number
    insufficient_evidence: number
    not_applicable: number
  }
}

export const VENDOR_1: Vendor = {
  id: 'vnd-hyd-001',
  name: 'Sri Lakshmi Kirana & General Stores',
  vendor_type: 'kirana',
  state: 'Telangana',
  region: 'Hyderabad Region',
  district: 'Hyderabad',
  address: 'Shop 4-2-118, Sultan Bazar, Hyderabad 500095',
  created_at: '2026-08-10T09:00:00+05:30',
}

export const VENDOR_2: Vendor = {
  id: 'vnd-hyd-002',
  name: 'Smart Point Supermarket - Kukatpally',
  vendor_type: 'supermarket',
  state: 'Telangana',
  region: 'Hyderabad Region',
  district: 'Medchal-Malkajgiri',
  address: 'Plot 12, Phase II, KPHB Colony, Hyderabad 500072',
  created_at: '2026-08-12T11:30:00+05:30',
}

export const VENDOR_3: Vendor = {
  id: 'vnd-hyd-003',
  name: 'Deccan Agro Wholesalers & Godown',
  vendor_type: 'godown',
  state: 'Telangana',
  region: 'Hyderabad Region',
  district: 'Rangareddy',
  address: 'Shed 8, Industrial Estate, Kattedan, Hyderabad 500077',
  created_at: '2026-08-15T14:20:00+05:30',
}

export const VENDOR_4: Vendor = {
  id: 'vnd-pun-001',
  name: 'Om Sai Provision Store',
  vendor_type: 'kirana',
  state: 'Maharashtra',
  region: 'Pune Region',
  district: 'Pune',
  address: '214 Narayan Peth, Laxmi Road, Pune 411030',
  created_at: '2026-08-18T10:00:00+05:30',
}

export const VENDOR_5: Vendor = {
  id: 'vnd-pun-002',
  name: 'Hypercity Retail Mart - Hadapsar',
  vendor_type: 'supermarket',
  state: 'Maharashtra',
  region: 'Pune Region',
  district: 'Pune',
  address: 'Amanora Town Centre, Hadapsar, Pune 411028',
  created_at: '2026-08-20T16:45:00+05:30',
}

export const VENDOR_6: Vendor = {
  id: 'vnd-nag-001',
  name: 'Vidarbha Central FMCG Godown',
  vendor_type: 'godown',
  state: 'Maharashtra',
  region: 'Nagpur Region',
  district: 'Nagpur',
  address: 'Warehouse Complex 3, MIDC Hingna Road, Nagpur 440028',
  created_at: '2026-08-22T08:15:00+05:30',
}

export const VENDOR_7: Vendor = {
  id: 'vnd-mum-001',
  name: 'Ganesh Kirana Bunder',
  vendor_type: 'kirana',
  state: 'Maharashtra',
  region: 'Konkan Region',
  district: 'Mumbai Suburban',
  address: 'Shop 7, JP Road, Andheri West, Mumbai 400058',
  created_at: '2026-08-25T13:10:00+05:30',
}

export const VENDORS: Vendor[] = [
  VENDOR_1,
  VENDOR_2,
  VENDOR_3,
  VENDOR_4,
  VENDOR_5,
  VENDOR_6,
  VENDOR_7,
]

export const VENDOR_SUBMISSIONS: VendorSubmissionItem[] = [
  {
    scan_id: 'scn-9011-a1b2',
    verdict_id: 'vrd-7011-c3d4',
    vendor: VENDOR_1,
    product_description: 'Refined sunflower oil, 1 L polypack',
    product_category: 'food',
    source_type: 'physical_label',
    captured_at: '2026-09-07T10:15:00+05:30',
    recommended_verdict: 'POTENTIAL_VIOLATION',
    routed_officer: {
      officer_id: 'KLM-HYD-04',
      name: 'R. K. Sharma',
      designation: 'Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Hyderabad District, Circle-II',
    },
    officer_confirmation: {
      is_confirmed: true,
      action: 'confirm',
      officer_id: 'KLM-HYD-04',
      confirmed_verdict: 'POTENTIAL_VIOLATION',
      confirmed_at: '2026-09-07T11:45:00+05:30',
      notes: 'Confirmed letter height measurement 1.9 mm falls below mandatory 2.5 mm under Rule 7(2) Table-I.',
    },
    manufacturer_name: 'Apex Agro Refining Private Limited',
    issue_summary: 'Net quantity declaration letter height measured at 1.9 mm, below 2.5 mm threshold for 1 L pack.',
    finding_counts: {
      pass: 8,
      review_required: 0,
      fail: 1,
      insufficient_evidence: 0,
      not_applicable: 2,
    },
  },
  {
    scan_id: 'scn-9012-e5f6',
    verdict_id: 'vrd-7012-g7h8',
    vendor: VENDOR_2,
    product_description: 'Skin moisturising cream, 100 g jar',
    product_category: 'cosmetics',
    source_type: 'physical_label',
    captured_at: '2026-09-07T14:30:00+05:30',
    recommended_verdict: 'POTENTIAL_VIOLATION',
    routed_officer: {
      officer_id: 'KLM-MED-03',
      name: 'M. S. Reddy',
      designation: 'Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Medchal-Malkajgiri District',
    },
    officer_confirmation: {
      is_confirmed: true,
      action: 'confirm',
      officer_id: 'KLM-MED-03',
      confirmed_verdict: 'POTENTIAL_VIOLATION',
      confirmed_at: '2026-09-07T16:00:00+05:30',
      notes: 'Customer care email and telephone number omitted from outer carton under Rule 6(1)(da).',
    },
    manufacturer_name: 'GlowCare Laboratories LLP',
    issue_summary: 'Mandatory consumer care address omitted email and contact telephone on cosmetic package.',
    finding_counts: {
      pass: 7,
      review_required: 0,
      fail: 1,
      insufficient_evidence: 0,
      not_applicable: 3,
    },
  },
  {
    scan_id: 'scn-9013-i9j0',
    verdict_id: 'vrd-7013-k1l2',
    vendor: VENDOR_3,
    product_description: 'Packaged Whole Wheat Atta, 10 kg bag',
    product_category: 'food',
    source_type: 'physical_label',
    captured_at: '2026-09-07T15:20:00+05:30',
    recommended_verdict: 'POTENTIAL_VIOLATION',
    routed_officer: {
      officer_id: 'KLM-RR-01',
      name: 'P. Venkat Rao',
      designation: 'Assistant Controller of Legal Metrology',
      jurisdiction_level: 'region',
      jurisdiction: 'Rangareddy Region',
    },
    // RAW MACHINE VERDICT - OFFICER CONFIRMATION PENDING (UI Rule 1)
    officer_confirmation: {
      is_confirmed: false,
      action: null,
      officer_id: null,
      confirmed_verdict: null,
      confirmed_at: null,
      notes: null,
    },
    manufacturer_name: 'Shree Annapurna Mills Corp',
    issue_summary: 'Preliminary OCR indicated missing Unit Sale Price (USP) under Rule 6(11).',
    finding_counts: {
      pass: 6,
      review_required: 1,
      fail: 1,
      insufficient_evidence: 0,
      not_applicable: 3,
    },
  },
  {
    scan_id: 'scn-9014-m3n4',
    verdict_id: 'vrd-7014-o5p6',
    vendor: VENDOR_4,
    product_description: 'Instant Masala Noodles combo, 4 x 70 g',
    product_category: 'food',
    source_type: 'catalogue_record',
    captured_at: '2026-09-06T11:00:00+05:30',
    recommended_verdict: 'REVIEW',
    routed_officer: {
      officer_id: 'MH-PUN-01',
      name: 'V. S. Kulkarni',
      designation: 'Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Pune District, Division-1',
    },
    officer_confirmation: {
      is_confirmed: true,
      action: 'override',
      officer_id: 'MH-PUN-01',
      confirmed_verdict: 'POTENTIAL_VIOLATION',
      confirmed_at: '2026-09-06T13:30:00+05:30',
      notes: 'Multi-piece package lacks individual quantity declaration required under Rule 24.',
    },
    manufacturer_name: 'SpicyBite Foods India Ltd',
    issue_summary: 'Multi-piece package omitted mandatory statement of quantity for each individual piece under Rule 24.',
    finding_counts: {
      pass: 7,
      review_required: 2,
      fail: 0,
      insufficient_evidence: 0,
      not_applicable: 2,
    },
  },
  {
    scan_id: 'scn-9015-q7r8',
    verdict_id: 'vrd-7015-s9t0',
    vendor: VENDOR_5,
    product_description: 'Digital Blood Pressure Monitor, Upper Arm',
    product_category: 'medical_device',
    source_type: 'physical_label',
    captured_at: '2026-09-06T16:00:00+05:30',
    recommended_verdict: 'PASS',
    routed_officer: {
      officer_id: 'MH-PUN-01',
      name: 'V. S. Kulkarni',
      designation: 'Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Pune District, Division-1',
    },
    officer_confirmation: {
      is_confirmed: true,
      action: 'confirm',
      officer_id: 'MH-PUN-01',
      confirmed_verdict: 'PASS',
      confirmed_at: '2026-09-06T17:15:00+05:30',
      notes: 'All mandatory declarations present, legible and verified against Medical Devices Rules schedule.',
    },
    manufacturer_name: 'HealthPulse Diagnostics Ltd',
    issue_summary: 'Full statutory conformity observed across all mandatory declaration panels.',
    finding_counts: {
      pass: 10,
      review_required: 0,
      fail: 0,
      insufficient_evidence: 0,
      not_applicable: 1,
    },
  },
  {
    scan_id: 'scn-9016-u1v2',
    verdict_id: 'vrd-7016-w3x4',
    vendor: VENDOR_6,
    product_description: 'Packaged Toothpaste, 150 g tube',
    product_category: 'cosmetics',
    source_type: 'physical_label',
    captured_at: '2026-09-05T09:40:00+05:30',
    recommended_verdict: 'POTENTIAL_VIOLATION',
    routed_officer: {
      officer_id: 'MH-NAG-02',
      name: 'A. T. Deshmukh',
      designation: 'Deputy Controller of Legal Metrology',
      jurisdiction_level: 'state',
      jurisdiction: 'Maharashtra State, Vidarbha Zone',
    },
    // RAW MACHINE VERDICT - UNCONFIRMED (UI Rule 1)
    officer_confirmation: {
      is_confirmed: false,
      action: null,
      officer_id: null,
      confirmed_verdict: null,
      confirmed_at: null,
      notes: null,
    },
    manufacturer_name: 'DentaClean Healthcare Ltd',
    issue_summary: 'Preliminary detection: Month and year of manufacture missing on crimp seal.',
    finding_counts: {
      pass: 8,
      review_required: 0,
      fail: 1,
      insufficient_evidence: 1,
      not_applicable: 1,
    },
  },
  {
    scan_id: 'scn-9017-y5z6',
    verdict_id: 'vrd-7017-a7b8',
    vendor: VENDOR_7,
    product_description: 'Packaged Drinking Water, 500 ml PET bottle',
    product_category: 'food',
    source_type: 'physical_label',
    captured_at: '2026-09-04T12:00:00+05:30',
    recommended_verdict: 'REVIEW',
    routed_officer: {
      officer_id: 'MH-MUM-03',
      name: 'S. N. Patil',
      designation: 'Senior Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Mumbai Suburban District',
    },
    // RAW MACHINE VERDICT - UNCONFIRMED (UI Rule 1)
    officer_confirmation: {
      is_confirmed: false,
      action: null,
      officer_id: null,
      confirmed_verdict: null,
      confirmed_at: null,
      notes: null,
    },
    manufacturer_name: 'AquaPure Bottlers Private Limited',
    issue_summary: 'Free space around net quantity declaration appears crowded under Rule 8(1) proviso.',
    finding_counts: {
      pass: 7,
      review_required: 2,
      fail: 0,
      insufficient_evidence: 1,
      not_applicable: 1,
    },
  },
  {
    scan_id: 'scn-9018-c9d0',
    verdict_id: 'vrd-7018-e1f2',
    vendor: VENDOR_1,
    product_description: 'Herbal Washing Powder, 1 kg poly pouch',
    product_category: 'food',
    source_type: 'physical_label',
    captured_at: '2026-09-03T15:10:00+05:30',
    recommended_verdict: 'POTENTIAL_VIOLATION',
    routed_officer: {
      officer_id: 'KLM-HYD-04',
      name: 'R. K. Sharma',
      designation: 'Inspector of Legal Metrology',
      jurisdiction_level: 'district',
      jurisdiction: 'Hyderabad District, Circle-II',
    },
    officer_confirmation: {
      is_confirmed: true,
      action: 'confirm',
      officer_id: 'KLM-HYD-04',
      confirmed_verdict: 'POTENTIAL_VIOLATION',
      confirmed_at: '2026-09-03T17:00:00+05:30',
      notes: 'Declared MRP lacks statutory inclusive-of-all-taxes qualification under Rule 6(1)(e).',
    },
    manufacturer_name: 'CleanStar Consumer Products Pvt Ltd',
    issue_summary: 'Retail sale price declaration omits "incl. of all taxes" words as mandated by Rule 6(1)(e).',
    finding_counts: {
      pass: 6,
      review_required: 1,
      fail: 1,
      insufficient_evidence: 0,
      not_applicable: 3,
    },
  },
]
