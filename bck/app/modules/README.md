# app.modules

**Owner:** @Abhiram-0910 (the package itself; each module below has its own owner)

One package per capability. Each is owned by one person and each owns its own vertical
slice — `router.py`, `service.py`, `repository.py`, `schemas.py` inside the package.

| Module | Owner |
|---|---|
| `vision` | @aksha08-ya |
| `extraction` | @krishbattula4 |
| `measurement` | @Abhiram-0910 |
| `rules` | @Abhiram-0910 |
| `tamper` | @adepushivasai901-ops |
| `evidence` | @Shiva-Kumar-Akula |

Modules are independent: none may import another. Shared types go in `app.contracts`,
shared infrastructure in `app.core`, and anything that needs two modules at once is a
`app.pipeline` concern. `lint-imports` enforces this in CI.

Adding a module means adding it to the independence contract in `bck/pyproject.toml`.
`tests/test_import_boundaries.py` fails if you forget.
