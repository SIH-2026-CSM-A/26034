# app.core

**Owner:** @Abhiram-0910

Infrastructure every module needs and none should re-implement: settings
(`pydantic-settings`, read from environment — see `bck/.env.example`), authentication,
the role hierarchy and jurisdiction scoping, and the cost ceilings every paid call
checks. The SQLAlchemy engine and session factory land here too, when something needs
one.

May import `app.contracts`. May not import `app.modules` or `app.pipeline`.

No business rules. If it knows what a Legal Metrology declaration is, it belongs in a
module, not here.

Import from the package, never from a file inside it:

```python
from app.core import Principal, RoleTier, get_current_principal, get_settings
```

## Three things that are load-bearing

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

## Scoping a query

`scope_to_jurisdiction` narrows a SELECT to what the principal may see — one equality
predicate per level their tier pins:

```python
statement = scope_to_jurisdiction(select(ScanRecord), principal, ScanRecord)
records = session.scalars(statement).all()
```

It constrains the statement it is handed and nothing else. A query that never passes
through it is not scoped, and no permission check elsewhere will notice. When there is a
persistence layer to put it in, the repository that owns the session should apply this on
the way past.

## Cost ceilings

`settings.cost_ceiling(provider)` is the one place a paid provider's budget lives, read
by name. It raises on a provider nobody has budgeted for rather than returning something
permissive. Cloud OCR ships at `0`.
