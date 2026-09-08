/**
 * Additive reference, sourced. Nothing here is a safety judgement.
 *
 * Names and functional classes follow the International Numbering System (INS) as
 * adopted by Appendix A of the Food Safety and Standards (Food Products Standards and
 * Food Additives) Regulations, 2011, which lists permitted additives by INS number.
 * Declaration requirements come from the Food Safety and Standards (Labelling and
 * Display) Regulations, 2020: regulation 5(5) requires every additive to be declared by
 * its class title with its INS number or specific name, and regulation 5(14)(viii)
 * requires sulphite to be declared as an allergen at 10 mg/kg or more (FSSAI FAQ on the
 * 2020 Regulations, questions 21 and 23, 23 June 2022).
 *
 * A code not in this list renders "not assessed". Adding an entry means adding its
 * source; an unsourced line about a real product is the one thing this file must not
 * carry.
 */

export interface AdditiveEntry {
  code: string
  name: string
  functionalClass: string
  /** A declaration requirement the regulation itself states, or null. */
  declaration: { requirement: string; citation: string } | null
  citation: string
}

const FPS_FA = 'FSS (Food Products Standards and Food Additives) Regulations, 2011, Appendix A'
const LD_5_5 =
  'FSS (Labelling and Display) Regulations, 2020, regulation 5(5): declared by class title with INS number or name'
const LD_5_14_viii =
  'FSS (Labelling and Display) Regulations, 2020, regulation 5(14)(viii): sulphite declared as an allergen at 10 mg/kg or more'

export const ADDITIVES: readonly AdditiveEntry[] = [
  {
    code: '223',
    name: 'Sodium metabisulphite',
    functionalClass: 'Preservative, antioxidant (a sulphite)',
    declaration: {
      requirement: 'Must be declared as an allergen where sulphite is present at 10 mg/kg or more.',
      citation: LD_5_14_viii,
    },
    citation: FPS_FA,
  },
  {
    code: '319',
    name: 'Tertiary butylhydroquinone (TBHQ)',
    functionalClass: 'Antioxidant',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
  {
    code: '472e',
    name: 'Diacetyltartaric and fatty acid esters of glycerol (DATEM)',
    functionalClass: 'Emulsifier, stabiliser',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
  {
    code: '500(ii)',
    name: 'Sodium hydrogen carbonate (sodium bicarbonate)',
    functionalClass: 'Raising agent, acidity regulator',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
  {
    code: '503(ii)',
    name: 'Ammonium hydrogen carbonate (ammonium bicarbonate)',
    functionalClass: 'Raising agent, acidity regulator',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
  {
    code: '330',
    name: 'Citric acid',
    functionalClass: 'Acidity regulator, antioxidant synergist',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
  {
    code: '322',
    name: 'Lecithins',
    functionalClass: 'Emulsifier, antioxidant',
    declaration: { requirement: 'Declared by class title with INS number or name.', citation: LD_5_5 },
    citation: FPS_FA,
  },
]

export function lookupAdditive(code: string): AdditiveEntry | undefined {
  const wanted = code.toLowerCase()
  return ADDITIVES.find((a) => a.code.toLowerCase() === wanted)
}
