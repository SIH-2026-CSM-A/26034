# app.contracts

**Owner:** @Abhiram-0910

The shared vocabulary: the Pydantic models and enums that cross a module boundary — the
extracted-declaration shape, the rule shape, the measurement shape, the verdict record.

This is the bottom layer. It imports nothing from `app` and depends on nothing but
Pydantic and the standard library. No framework, database or I/O code belongs here — only
types. `lint-imports` enforces the direction in CI; it is not a convention.

## Importing

Import from the package, never from a file inside it:

```python
from app.contracts import DeclarationField, FieldState, VerdictRecord
```

The split into `enums.py`, `evidence.py`, `measurement.py`, `rules.py` and `records.py` is
internal. Going through the package surface means rearranging files here is not a change
to six other people's imports.

## What v1 holds

| Type | What it is |
|---|---|
| `FieldState` | Per-field outcome. Exactly five states. |
| `Verdict` | Package-level recommendation. Exactly three. |
| `DeclarationField` | The Rule 6 declaration set, one member per obligation. |
| `EvidenceProvider` | What produced a value — which OCR engine, artwork, catalogue, or an officer. |
| `RuleStatus`, `RuleSeverity`, `ToleranceBasis` | Rule metadata vocabularies. |
| `ExtractedSpan` | Text located on an image by a provider. Raw observation. |
| `NormalisedField` | A declaration resolved from spans into a canonical value. |
| `MeasurementExact` / `MeasurementCalibrated` / `MeasurementRefusal` | The three measurement modes, as a discriminated union `MeasurementResult`. |
| `RuleDefinition`, `RuleSetVersion` | An encoded provision and the published set it ships in. |
| `RuleParameterSnapshot` | A rule's parameters copied by value at evaluation time. |
| `FieldFinding`, `VerdictRecord` | One finding, and the complete evidence record. |
| `CatalogueRecord` | A structured listing — the non-image ingestion path. |

## Four things that are load-bearing

**`INSUFFICIENT_EVIDENCE` is not `FAIL`.** FAIL says the declaration was read and falls
short. INSUFFICIENT_EVIDENCE says we could not read it. One is a defect in the package,
the other a defect in our reading of it, and only the first can support enforcement.
Collapsing them is a wrongful-flag liability. Do not map them onto each other anywhere.

**A verdict record holds rule parameters by value.** `VerdictRecord` carries no
`rule_definition_id`, no `rule_set_id`, and must never gain one. Every parameter that
shaped a finding is snapshotted onto it via `RuleParameterSnapshot.from_rule()`. Joining a
stored verdict back to a live rules table would re-adjudicate history — an amendment
landing on Tuesday silently changing what Monday's scan is recorded as having found. The
type is shaped this way so the persistence layer has no other option.

**Rounding increment and tolerance are two fields, never one.** An increment transforms a
value in steps; a tolerance accepts a difference. They diverge at every boundary. A
tolerance additionally requires a `tolerance_basis`, because `Decimal("0.05")` on its own
is either five paise or five percent — the First Schedule states maximum permissible error
as a percentage, while money tolerances are absolute.

**A rule with no `gazette_ref` fails to construct.** Not flagged later — rejected at
construction, so an unsourced rule number cannot reach an evaluator at all. What is *not*
checked here is that the reference names a file that exists in `rules-corpus/`: contracts
does no I/O, so the rule loader owns that check.

## Changing something here

Only @Abhiram-0910 edits this package. If a field you need is missing, comment on your
ClickUp ticket. Do not add it locally — a local addition passes your tests and breaks
someone else's merge, and the type then means two different things in two modules.

Every change ships with a PR that names the modules affected, because changing a type here
changes it for all of them at once.
