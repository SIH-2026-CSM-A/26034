/**
 * Fixture: one verdict record with six findings, and the spans those findings
 * cite. Not live data — see README.md in this directory.
 *
 * Replaced by a fetch against the real endpoint at PIP-002. The route component
 * is the only place that imports this; no component below it does.
 */

import {
  DeclarationField,
  EvidenceProvider,
  FieldState,
  Verdict,
  type ExtractedSpan,
  type Point,
  type RuleParameterSnapshot,
  type VerdictRecord,
} from './contracts'

const RULE_SET_VERSION = '2026.02.1'

/** Nominal capture dimensions. Every polygon below is in this pixel space. */
export const CAPTURE_SIZE = { width: 1000, height: 1400 } as const

/**
 * The principal display panel as detected on the capture. The second register
 * draws it so the officer can see what area the letter-height bands were
 * resolved against — 180 cm² puts this package in Table-I's 100–500 cm² band.
 */
export const PDP_OUTLINE: readonly Point[] = [
  [118, 176],
  [886, 152],
  [902, 1092],
  [132, 1118],
]

/**
 * The region the retail sale price declaration was searched for in, and not
 * resolved from. Drawn as an unresolved search area rather than a span,
 * because there is no span: nothing was read here.
 *
 * This is the whole argument of the INSUFFICIENT EVIDENCE state made visible.
 * The system looked, came back with nothing, and says so — rather than
 * producing a millimetre figure it cannot justify.
 */
export const UNRESOLVED_REGION: readonly Point[] = [
  [156, 858],
  [560, 846],
  [566, 1000],
  [162, 1012],
]

function snapshot(
  ruleId: string,
  clauseRef: string,
  gazetteRef: string,
  sourceText: string,
): RuleParameterSnapshot {
  return {
    rule_id: ruleId,
    clause_ref: clauseRef,
    gazette_ref: gazetteRef,
    source_text: sourceText,
    status: 'VERIFIED',
    severity: 'MANDATORY',
    rule_set_version: RULE_SET_VERSION,
  }
}

const LMPC = 'LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf'
const GSR_629E = 'GSR-629E__2017-06-23__amendment-rules-2017.pdf'

const RULE_7_2 = snapshot(
  'R7-2-TABLE-I',
  'Rule 7(2), Table-I',
  GSR_629E,
  'The height of any numeral and letter in the declaration required under these rules ' +
    'shall be as per Table-I.',
)

const RULE_6_11 = snapshot(
  'R6-11',
  'Rule 6(11)',
  LMPC,
  'The unit sale price shall be declared on the package, on the unit basis keyed to ' +
    'the net quantity declared.',
)

const RULE_6_1_A = snapshot(
  'R6-1-A',
  'Rule 6(1)(a)',
  LMPC,
  'the name and address of the manufacturer, or where the manufacturer is not the ' +
    'packer, the name and address of the manufacturer and packer and for any imported ' +
    'package the name and address of the importer shall be mentioned on every package.',
)

const RULE_8_1 = snapshot(
  'R8-1-FREE-SPACE',
  'Rule 8(1) proviso',
  LMPC,
  'Provided that the area surrounding the quantity declaration shall be free from ' +
    'printed information. (a) above and below by a space equal to at least the height ' +
    'of the numeral in the declaration, and (b) to the left and right by a space at ' +
    'least twice the height of numeral in the declaration.',
)

const RULE_6_1_AA = snapshot(
  'R6-1-AA',
  'Rule 6(1)(aa)',
  LMPC,
  'The name of the country of origin or manufacture or assembly, in the case of ' +
    'imported products, shall be mentioned on the package.',
)

/**
 * The spans the findings cite. Confidence and polygon live here, not on the
 * finding — a row resolves both through `evidence_span_ids`, which is why the
 * two rows that cite no spans show no confidence figure and pin no polygon.
 */
export const spans: readonly ExtractedSpan[] = [
  {
    span_id: 'span-netqty-height',
    text: 'Net quantity: 250 g',
    polygon: [
      [188, 604],
      [706, 590],
      [710, 668],
      [192, 682],
    ],
    confidence: 0.94,
    source_provider: EvidenceProvider.PADDLEOCR,
    region_id: 'pdp-front',
  },
  {
    span_id: 'span-unit-price',
    text: 'Rs. 5.00 per 100 g',
    polygon: [
      [188, 720],
      [640, 710],
      [644, 780],
      [192, 790],
    ],
    confidence: 0.88,
    source_provider: EvidenceProvider.PADDLEOCR,
    region_id: 'pdp-front',
  },
  {
    span_id: 'span-name-address',
    text: 'Manufactured by — name and address as declared on the package',
    polygon: [
      [180, 250],
      [842, 232],
      [850, 430],
      [186, 448],
    ],
    confidence: 0.97,
    source_provider: EvidenceProvider.PADDLEOCR,
    region_id: 'pdp-front',
  },
  {
    span_id: 'span-netqty-block',
    text: 'Net quantity: 250 g',
    polygon: [
      [166, 566],
      [746, 550],
      [752, 706],
      [172, 722],
    ],
    confidence: 0.79,
    source_provider: EvidenceProvider.PADDLEOCR,
    region_id: 'pdp-front',
  },
]

export const verdictRecord: VerdictRecord = {
  subject_ref: 'SCAN-2026-0914-FIXTURE',
  verdict: Verdict.POTENTIAL_VIOLATION,
  rule_set_version: RULE_SET_VERSION,
  evaluated_at: '2026-09-06T09:14:22+05:30',
  field_providers: {
    [DeclarationField.NET_QUANTITY]: EvidenceProvider.PADDLEOCR,
    [DeclarationField.UNIT_SALE_PRICE]: EvidenceProvider.PADDLEOCR,
    [DeclarationField.NAME_AND_ADDRESS]: EvidenceProvider.PADDLEOCR,
  },
  findings: [
    {
      field: DeclarationField.NET_QUANTITY,
      state: FieldState.FAIL,
      rule_snapshot: RULE_7_2,
      observed_value: '2.1 mm',
      expected_value: '≥ 2.5 mm',
      reason:
        'Measured against a ₹10 coin in frame, PDP area 180 cm². The letters of the ' +
        'net quantity declaration fall short of the height Table-I requires at this ' +
        'panel area.',
      evidence_span_ids: ['span-netqty-height'],
    },
    {
      field: DeclarationField.UNIT_SALE_PRICE,
      state: FieldState.FAIL,
      rule_snapshot: RULE_6_11,
      observed_value: 'Rs. 5.00 per 100 g',
      expected_value: 'Rs. per g',
      reason:
        'Basis read from the declaration, not weighed. The unit basis declared is not ' +
        'the basis the rule keys to this net quantity.',
      evidence_span_ids: ['span-unit-price'],
    },
    {
      field: DeclarationField.NAME_AND_ADDRESS,
      state: FieldState.PASS,
      rule_snapshot: RULE_6_1_A,
      observed_value: null,
      expected_value: null,
      reason:
        'Name and address of the manufacturer are present and legible on the principal ' +
        'display panel.',
      evidence_span_ids: ['span-name-address'],
    },
    {
      field: DeclarationField.NET_QUANTITY,
      state: FieldState.REVIEW_REQUIRED,
      rule_snapshot: RULE_8_1,
      observed_value: '1.8 mm below',
      expected_value: '≥ 2.1 mm',
      reason:
        'The proviso requires free space above and below equal to at least the height ' +
        'of the numeral, measured here at 2.1 mm. The space below is short of that by ' +
        'a margin inside the measurement uncertainty at this capture, so an officer ' +
        'has to resolve it.',
      evidence_span_ids: ['span-netqty-block'],
    },
    {
      field: DeclarationField.COUNTRY_OF_ORIGIN,
      state: FieldState.NOT_APPLICABLE,
      rule_snapshot: RULE_6_1_AA,
      observed_value: null,
      expected_value: null,
      reason:
        'Manufactured in India. The clause reaches imported products, so no country of ' +
        'origin declaration is owed on this package.',
      evidence_span_ids: [],
    },
    {
      field: DeclarationField.RETAIL_SALE_PRICE,
      state: FieldState.INSUFFICIENT_EVIDENCE,
      rule_snapshot: RULE_7_2,
      observed_value: 'not determinable — no reference object in frame',
      expected_value: '≥ 2.5 mm',
      reason:
        'No reference object in frame, so there is no scale to measure letter height ' +
        'against. Recapture with a ₹10 coin in frame.',
      evidence_span_ids: [],
    },
  ],
}

/** Masthead furniture. Connectivity is a property of the device, not the record. */
export const captureContext = {
  inspectionId: 'INSP-MH-2026-04417',
  capturedAt: '2026-09-06T09:11:48+05:30',
  /** Fixed in the fixture so the offline marker is visible while it is built. */
  online: false,
} as const
