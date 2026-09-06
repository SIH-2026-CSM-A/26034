# app.pipeline

**Owner:** @Abhiram-0910

The only place that composes modules. An image comes in; vision, extraction,
measurement, tamper and rules run in order; evidence assembles the result.

`app.main` sits above this and mounts `scan_router`; nothing below may import either.
That asymmetry is deliberate: a module can be read, tested and reviewed without knowing
where it sits in the run.

## Layout

| File | Holds |
|---|---|
| `orchestrator.py` | Stage order, and the two entry points. Pure: no session, no clock. |
| `capture.py` | What an officer is told when the quality gate refuses a photograph. |
| `dispositions.py` | What *kind* of obligation each rule states. Tables only. |
| `rule_findings.py` | One rule plus the evidence, into findings. |
| `measurement_findings.py` | The rules that state a physical threshold — the one place a millimetre may be emitted. |
| `findings.py` | The pass over the active rule set. |
| `normalisation.py` | Declared text into `NormalisedField`. |
| `rule_snapshot.py` | `rules.RuleDefinition` into `contracts.RuleParameterSnapshot`. |
| `verdict.py` | Findings into a `VerdictRecord`. |
| `router.py` · `schemas.py` · `repository.py` · `responses.py` | The HTTP surface. |

## Two things to know before editing

**The sector gate runs before every builder.** With no confirmed product category, every
rule in `SECTOR_GOVERNED_RULES` is settled as INSUFFICIENT_EVIDENCE before its own builder
is reached. A test asserting something about Rule 7's measurement handling while leaving
the category unconfirmed passes whether or not that handling exists — four tests were
written that way here before being caught. Confirm a category that carves nothing out, or
assert against a rule the gate does not touch.

**There are no `relationship()` declarations on the models, so insert order is not
automatic.** `repository.add_verdict` flushes the verdict before its findings, deliberately.
Copy that pattern for any other parent/child write rather than adding a relationship: on an
async mapper they lazy-load on attribute access and raise `MissingGreenlet` while the
response is being serialised.
