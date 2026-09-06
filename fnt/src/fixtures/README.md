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

- **Rule 7(2) Table-I, ≥ 2.5 mm at a PDP area of 180 cm².** Confirmed against
  `rules-corpus/README.md`, which records Table-I as banded by principal display panel
  area since G.S.R. 629(E) w.e.f. 01.01.2018, with the band `100 < A ≤ 500 cm²`
  requiring 2.5 mm for normal (non-blown, non-moulded) lettering. 180 cm² falls in that
  band. Both letter-height findings cite it.

The `gazette_ref` on every snapshot names a real file in `rules-corpus/`. No rule number,
threshold or gazette reference appears here that was not either supplied on the ticket or
read out of the corpus.

`status` and `severity` are fixture values. Neither is rendered — the authoritative
status of an encoded rule belongs to the rules module, and the officer surface must not
appear to grade a contravention. They are present only because the contract carries them.

## Product descriptions

The queue rows describe commodity types — "Refined sunflower oil, 1 L" — and never a
brand or a manufacturer. A fabricated brand name sitting in a compliance queue reads as a
real finding against a real company, which is not something a fixture is allowed to look
like.
