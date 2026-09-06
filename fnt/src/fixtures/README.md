# fixtures

Fixture data for the officer surface. **This is not live data and it is not a mock
layer.** It is a fixed, hand-written record used to build and review the screens before
`PIP-002` exposes the real endpoint.

Everything here is deliberately obvious about being a fixture: the files are named
`*.fixture.ts`, the capture register is a drawn diagram labelled *Fixture capture* in the
frame rather than a photograph, and the inspection id is a fixture id.

## What is here

| File | What it holds |
|---|---|
| `contracts.ts` | A hand-written TypeScript mirror of the backend `app.contracts` package. |
| `verdict-detail.fixture.ts` | One `VerdictRecord` with six findings, and the spans they cite. |
| `review-queue.fixture.ts` | Forty queue rows — verdict, confidence, product, date. |

## When this goes away

`contracts.ts` is a stand-in with a known expiry. The real client is generated from the
backend OpenAPI schema into `src/services/generated/`. When that lands, `contracts.ts` is
deleted and the imports repointed — it is not a parallel definition to be maintained
alongside the generated one. Field names are already snake_case for that reason; nothing
here renames a contract field.

The fixtures themselves are replaced by a fetch against the real endpoint at `PIP-002`.
Components take their data as props and none of them import a fixture directly, so that
swap happens at the two route components and nowhere else.

## Provenance of the rule citations

Rule numbers and thresholds are never written from memory. The six findings carry the
citations supplied on the FNT-002 ticket, and one of them was additionally confirmed
against `rules-corpus/` during the session that wrote this file:

- **Rule 7(2), Table-I — ≥ 2.5 mm at a PDP area of 180 cm².** Confirmed twice: against
  `rules-corpus/README.md`, and against the encoded `R7-2-TABLE-I` band
  `100 < A ≤ 500 cm² → 2.5 mm normal` in `bck/app/modules/rules/data/rules.yaml`.
  180 cm² falls in that band. Both letter-height findings cite it.

### Aligned to the encoded rule set, not to the ticket text

`RUL-002` landed the Rule 8 and Rule 9 encodings on `main` while this ticket was being
built. Four of the six findings correspond to rules that now exist in
`bck/app/modules/rules/data/rules.yaml`, so their `rule_id`, `clause_ref` and
`source_text` are taken from there verbatim rather than from the ticket:

| Finding | Ticket said | Encoded as |
|---|---|---|
| Net quantity / retail sale price letter height | `Rule 7(2) Table-I` | `R7-2-TABLE-I` · `Rule 7(2), Table-I` |
| Free space around the quantity declaration | `Rule 8(1)` | `R8-1-FREE-SPACE` · `Rule 8(1) proviso` |
| Manufacturer name and address | `Rule 6(1)(a)` | `R6-1-A` · `Rule 6(1)(a)` |
| Country of origin | `Rule 6(1)(aa)` | `R6-1-AA` · `Rule 6(1)(aa)` |

The two that moved are the same provisions under their authoritative references. `Rule 8`
now distinguishes two limbs — `R8-1-PDP-PLACEMENT` governs *where* a declaration appears,
`R8-1-FREE-SPACE` governs the space around it — and this finding is about the second, so
it cites the proviso. A fixture citing the wrong limb would have surfaced as a mismatch
the day `PIP-002` wires the real endpoint.

The encoded proviso also explains the ticket's `≥ 2.1 mm`: it requires free space above
and below "equal to at least the height of the numeral in the declaration", and the
numeral is measured at 2.1 mm in the first finding. The threshold is derived, not fixed,
and the finding's reason now says so.

**Rule 6(11) is not yet encoded.** There is no `R6-11` in `rules.yaml`; unit sale price is
still outstanding. Its snapshot carries the ticket's citation and an id in the module's
own naming convention, and should be re-checked against the encoded rule when one lands.

The `gazette_ref` on every snapshot names a real file in `rules-corpus/`. No rule number,
threshold or gazette reference appears here that was not either supplied on the ticket,
read out of the corpus, or copied from the encoded rule set.

`status` and `severity` are fixture values. Neither is rendered — the authoritative
status of an encoded rule belongs to the rules module, and the officer surface must not
appear to grade a contravention. They are present only because the contract carries them.

## Product descriptions

The queue rows describe commodity types — "Refined sunflower oil, 1 L" — and never a
brand or a manufacturer. A fabricated brand name sitting in a compliance queue reads as a
real finding against a real company, which is not something a fixture is allowed to look
like.
