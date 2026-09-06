# app.core

**Owner:** @Abhiram-0910

Infrastructure every module needs and none should re-implement: settings
(`pydantic-settings`, read from environment — see `bck/.env.example`), authentication,
the role hierarchy and jurisdiction scoping, the cost ceilings every paid call checks,
and the database — the engine and session factory in `db.py`, the declarative base and
column plumbing in `schema.py`, the storage vocabularies in `enums.py`, the tables in
`models.py`.

May import `app.contracts`. May not import `app.modules` or `app.pipeline`.

No business rules. If it knows what a Legal Metrology declaration is, it belongs in a
module, not here.

Import from the package, never from a file inside it:

```python
from app.core import Principal, RoleTier, get_current_principal, get_settings
```

## Why the tables are here

`models.py` sits uneasily beside the rule below that `core` holds no business rules: a
`FieldFindingRow` keyed by `DeclarationField` plainly knows what a Legal Metrology
declaration is. It is here anyway, and deliberately, because every alternative is worse.
No module owns persistence; modules may not import one another, so a schema shared
between them cannot live in any of them; and Alembic needs one stable `MetaData` to point
at. `core` is the only place that satisfies all three.

`field_findings.rule_id` is the one deliberate denormalisation: a copy of a single field
of the `rule_snapshot` document beside it. The snapshot remains the record of what was
applied — this is a queryable copy, written from `rule_snapshot["rule_id"]` and from
nowhere else. It earns a column because `(verdict_id, field)` is correctly *not* unique
(one declaration is evaluated against several rules) while `(verdict_id, field, rule_id)`
is, and that constraint cannot be stated about a value living inside a JSON document. It
is not a foreign key and there is no rules table for it to point at.

The line that still holds is the one that matters: these are *tables*, not rules. Nothing
in `models.py` decides an outcome, and nothing in it may. `contracts` holds the shapes
that cross a module boundary and `models.py` the shapes that cross a process restart; the
enums appear in both because they are imported from `contracts`, never restated, so a
state cannot mean one thing in memory and another on disk.

## Insert order is not automatic here

**There is no `relationship()` on any model, and that is a choice.** SQLAlchemy orders
dependent inserts from relationship declarations, not from `ForeignKey` columns, so a
parent and its children added in the same flush can be emitted child-first and rejected by
the database. `pipeline/repository.add_verdict` therefore flushes the verdict before adding
its findings, explicitly.

Adding relationships would fix the ordering and buy a worse problem: on an async mapper a
relationship lazy-loads on attribute access and raises `MissingGreenlet`, normally while
the response is being serialised, a long way from the code that touched it. The same
reasoning as `expire_on_commit=False` in `db.py`. If a second parent/child write appears,
copy the explicit flush.

## Five things that are load-bearing

**The hierarchy is one ordered enum, not three roles.** `RoleTier` has `STATE`,
`REGIONAL` and `DISTRICT`, broadest first, and both `rank` and `scope_fields` are derived
from that order. There is no `is_controller()` to keep in step with an `is_inspector()`.
A permission check is `tier.covers(minimum)`.

**Designations are configuration.** The three tiers are structural and fixed; what a
state calls them is not, and the pilot state is not chosen. Every title comes from
`Settings.designation(tier)`, driven by `ROLE_DESIGNATIONS`. Nothing outside the default
in `config.py` spells out "Controller" or "Inspector" — a check that compared against one
of those words would break the first time a state used a different title.

**A principal comes from a verified token and from nowhere else.** `principal_from_token`
verifies the signature against an explicit algorithm allowlist, requires an expiry, and
then rebuilds the `Principal` through its own validation, so a tampered jurisdiction is
refused even when the signature is intact. A tier or jurisdiction in a request body is
the client describing its own authority; no endpoint may act on one.

**A session lasts one request, and the dependency does not commit.** `get_session` opens
one, yields it to a single handler and closes it; committing is the caller's, because a
teardown-commit fires after the response body is built — a failure at that point cannot
change the status code the client already has, and it commits work the handler may have
decided to abandon. There is no module-level session and no engine built at import time:
`get_engine` and `get_session_factory` are `lru_cache`d the way `get_settings` is, so a
missing `DATABASE_URL` fails at first use with a message naming the setting.

**One DSN string serves both the app and Alembic.** `postgresql+psycopg://` is valid for
`create_engine` and `create_async_engine` alike — SQLAlchemy picks the mode from the
constructor, not from the URL. The application runs async, `alembic/env.py` runs the same
string synchronously, and neither rewrites the other's scheme. The `+psycopg` suffix is
required: bare `postgresql://` resolves to psycopg2, which is not installed.

## Scoping a query

`scope_to_jurisdiction` narrows a SELECT to what the principal may see — one equality
predicate per level their tier pins:

```python
statement = scope_to_jurisdiction(select(ScanRecord), principal, ScanRecord)
records = session.scalars(statement).all()
```

It constrains the statement it is handed and nothing else. A query that never passes
through it is not scoped, and no permission check elsewhere will notice — `get_session`
does not apply it either. `Scan` carries `state`, `region` and `district` as three real
columns with exactly those names because this function reaches them by `getattr`; folding
them into a JSON document would make every scoped query raise. Closing the remaining hole
properly means a repository that owns the session and applies this on the way past, which
waits for a module with a caller for one.

## Model weights are checked at startup

`Settings.missing_model_paths()` names any of `pdp_weights_path`, `ocr_det_model_dir` and
`ocr_rec_model_dir` that is unset or absent on disk. `app/main.py`'s lifespan calls it once
and refuses to start when it returns anything.

Once, at boot, and never as a fallback. `detect_pdp` and `extract_panel_text` raise
`FileNotFoundError` without their weights, so the alternative is a 500 on an officer's
first scan — and substituting a different stage would produce a verdict by a path nobody
chose. Weights are gitignored and pre-cached, so the case this guards is a fresh clone.

## Cost ceilings

`settings.cost_ceiling(provider)` is the one place a paid provider's budget lives, read
by name. It raises on a provider nobody has budgeted for rather than returning something
permissive. Cloud OCR ships at `0`.
