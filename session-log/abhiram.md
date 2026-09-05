# Session log — Abhiram

### 2026-09-05 — CTR-002 contracts v1 — Claude Code

**Done**
- `bck/app/contracts/` v1, six modules behind one import surface: `base.py`
  (`ContractModel`, `extra="forbid"` + `frozen=True`), `enums.py`, `evidence.py`,
  `measurement.py`, `rules.py`, `records.py`, re-exported from `__init__.py` with
  `__all__` so consumers write `from app.contracts import X` and file moves inside the
  package are not a nine-way breaking change.
- `bck/tests/contracts/test_contracts.py` — 36 tests, written as the properties the
  other tickets depend on rather than as field-spelling checks.
- Naming sweep: product name settled as **PCCS — Packaged Commodity Compliance System**
  across README, ARCHITECTURE, AGENTS, CLAUDE and TODO. The case-insensitive sweep for
  the old placeholder name is clean from the repo root.

**Decided**
- `DeclarationField` is one member per Rule 6 clause, not per role. 6(1)(a) is a single
  obligation covering manufacturer, packer and importer, and by Explanation II the
  marketer or brand owner too. Which role a declaration was made under is a property of
  the extracted value — `AddressRole` in extraction already models it. Rejected fifteen
  role-shaped members: it turns one obligation into five findings an officer has to
  reconcile. Clause letters read out of the Maharashtra compilation during the ticket,
  not from memory.
- Measurement variant names stay Yashashvi's — `MeasurementExact` /
  `MeasurementCalibrated` / `MeasurementRefusal`, discriminated on `mode`. The ticket
  offered `ExactFromArtwork` / `CalibratedEstimate` / `Refused`. Rejected, because her
  MEA-001 shape is merged and tested and matching it exactly makes MEA-002 a
  delete-and-import instead of a rewrite. Verified field-for-field and by replaying every
  construction site in her `services.py` against the contracts models.
- `tolerance` requires `tolerance_basis`. The First Schedule states maximum permissible
  error as a percentage of declared quantity; a money tolerance is an absolute amount.
  `Decimal("0.05")` alone is either five paise or five percent, so a bare figure now
  fails to construct. Rejected storing one pre-resolved number — it cannot be re-derived
  from the gazette text afterwards.
- `rounding_increment` and `tolerance` are separate fields. An increment transforms a
  value in steps, a tolerance accepts a difference; they diverge at every boundary. Rule
  6(11) uses neither — `rules-corpus/README.md` establishes it is a format rule — but
  the schema has to express both for the rules that do.
- `EvidenceProvider` is a closed enum rather than a free string. Cost: Akshaya files a
  contracts ticket to add a provider. Benefit: the evidence chain cannot carry "paddle",
  "PaddleOCR" and "paddleocr" as three providers.
- `VerdictRecord` carries no `rule_definition_id` or `rule_set_id` and a test asserts the
  field names stay absent. Snapshots go on via `RuleParameterSnapshot.from_rule()`.
- Two deliberate departures from the ticket's field list, both flagged in the PR:
  `NormalisedField.span_refs` is plural, because an address is read as several spans and
  a singular ref leaves the evidence chain unable to cite what was used; and
  `numeric_value: Decimal | None` sits alongside `normalised_value: str`, because PR #4
  review already forced `NetQuantityValue.value` to `Decimal` for First Schedule
  comparisons and re-parsing a number out of a string at each comparison site undoes that.

**Hit**
- Another session committed on this branch mid-ticket: `docs: sync HANDOFF and TICKETS`
  landed on `feature/26034-CTR-002-contracts-v1`, was moved to `docs/sync-handoff-tickets`,
  and the branch was `reset --hard HEAD~1`. The reset reverted every edit I had made to
  *tracked* files — the contracts `__init__.py` and README, and the four doc headings —
  while the new untracked modules survived and were committed as a WIP checkpoint. Redone
  and verified. This is the hazard AGENTS.md warns about; a worktree would have prevented
  it, and I should use one whenever another agent is live on this repo.
- That sync commit also added a HANDOFF.md note quoting the old placeholder product name
  literally, which trips the CTR-002 sweep. It is not on this branch, so it is not mine to
  fix here — `docs/sync-handoff-tickets` needs the note rephrased before it merges, or
  the naming sweep goes dirty again on main.

**Verified rather than assumed**
- Mutation-tested the four guard tests: added a documented sixth `FieldState` member, a
  documented fourth `Verdict` member, an undocumented enum member, and a `rule_set_id`
  field on `VerdictRecord`. Each made exactly the intended test fail; each was reverted.
  A test that passes the moment it is written is a test that has not been shown to fail.
- Proved the import boundary instead of eyeballing it: added `from app.core import ...`
  and then `from app.modules.measurement import ...` to a contracts module. `lint-imports`
  exited 1 naming the violation both times, exits 0 clean.

**Incomplete**
- `tamper/` and `evidence/` have no contract types of their own yet — nothing crosses a
  boundary from them until EVD-002 and the tamper ticket exist. Deliberate, not forgotten.
- `PackageShape` stays local to measurement. It does not cross a boundary today; the rules
  module consumes a PDP *area*, not a shape.

### 2026-09-05 — VP-CI-001 repo scaffold — Claude Code

**Done**
- `bck/` package skeleton: `contracts`, `core`, `pipeline`, and six module packages under
  `modules/`. Every directory has a README naming its owner.
- `bck/pyproject.toml` — Python 3.11, uv, FastAPI stack, dev group, ruff (line 100,
  py311, E/F/I/N/UP/B/SIM), and the two import-linter contracts.
- `.github/workflows/ci.yml` — ruff check, ruff format --check, lint-imports, pytest on
  every PR, with uv cached against `bck/uv.lock`.
- `.github/CODEOWNERS`, `.gitignore`, `bck/.env.example`, `AGENTS.md`, root `README.md`.
- Fixed `.github/workflows/claude.yml` re-triggering on its own replies
  (`github.actor != 'claude'` guard around the existing condition).
- Verified the boundary rather than assuming it: added
  `from app.modules import rules` to `vision/__init__.py`, `lint-imports` exited 1 naming
  the violation, removed it, re-ran the full set green. Also confirmed
  `test_import_boundaries.py` fails when a module package exists without a contract entry.

**Decided**
- Layers nest inside each module (`router.py`/`service.py`/`repository.py`/`schemas.py`),
  not as top-level `api/`/`services/`/`repositories/`. Deviation from T3 §4, recorded in
  AGENTS.md. Reason: ten owners; horizontal layers make every ticket a three-way
  ownership collision. Rejected the T3 layout for that reason — do not re-propose it.
- Base branch is `main`. T4's develop→staging→release→production chain is superseded here;
  one environment does not justify a four-branch promotion chain.
- No empty `router.py`/`service.py` files. The ticket bars stubs, so the layer convention
  is documented in each module README instead of pre-created as empty files.
- `bck` is installed as a real package (hatchling) rather than relying on cwd being on
  `sys.path` — `lint-imports` is a console script and would not have found `app` otherwise.
- Rejected a `docs/` directory (T3 §3 checklist) for now — nothing to put in it yet, and
  an empty one is exactly the placeholder the ticket rules out.

**Incomplete**
- Alembic not initialised — `bck/alembic/` is `.gitkeep` + README. Separate ticket.
- No application entrypoint; `uv run uvicorn app.main:app` in the README is the target,
  not something that runs today.
- GitHub usernames unconfirmed for `measurement` and `rules`; both fall back to
  @Abhiram-0910 in CODEOWNERS and AGENTS.md. Update both files together when known.
- Branch protection on `main` (PR-only, CI green) is a GitHub settings change, not a file
  — still needs doing in the repo settings.
