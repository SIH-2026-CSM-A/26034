# ClauseCam

**PCCS — Packaged Commodity Compliance System — is this repository's technical name; ClauseCam is what the system is called.**

**SIH 2026 · problem statement 26034 · Legal Metrology (Packaged Commodities) Rules, 2011**

ClauseCam reads a photograph of a packaged commodity — or an e-commerce catalogue listing — and
reports, declaration by declaration, whether the label carries what the Legal Metrology
(Packaged Commodities) Rules, 2011 require of it. Every finding names the clause it comes
from, the value read off the label and the evidence it was read from, and no finding is a
decision: the machine reaches a recommendation, a Legal Metrology officer confirms or
overturns it, and the officer's determination is what enters the record.

## Live demo

**<https://locally-progress-major-bare.trycloudflare.com>**

A Cloudflare tunnel to the demo VM, which runs the same `docker-compose.prod.yml` stack
described below. The URL changes whenever the tunnel is restarted.

- `/consumer` is public. Upload a photograph of any packaged food label; no sign-in.
- `/login` is the officer surface, `/vendor/login` the vendor surface. Both pages carry a
  "Demo access" panel with one-click sign-in. The demo accounts are public on purpose and
  sit in their own jurisdiction (Telangana / Demo Region / Demo District), so they see only
  seeded demonstration data:

  | Surface | Username | Password |
  |---|---|---|
  | Officer, `/login` | `demo-officer` | `clausecam-demo` |
  | Vendor, `/vendor/login` | `demo-vendor` | `clausecam-demo` |

Two full screen recordings of the system being driven end to end, one phone and one
desktop, with per-step timestamps and the scan ids each pass created: **[demo/README.md](demo/README.md)**.

## What runs today

Backend, all of it reachable through the OpenAPI schema at `/docs`:

- **Image scan.** PaddleOCR text detection and recognition over the submitted photograph,
  with a character-whitelisted Tesseract re-read on the retail sale price and the net
  quantity, where an `8`-for-`B` is not tolerable. Spans are normalised into declaration
  fields and bound to the text they came from.
- **Rule evaluation.** 29 encoded rules, rule set version `2026.09.2`, each citing the
  gazette clause it derives from. The evaluator is deterministic Python over a YAML rule
  store — no model and no agent sits anywhere on the verdict path. Each field lands in one
  of `PASS`, `FAIL`, `REVIEW_REQUIRED`, `NOT_APPLICABLE` or `INSUFFICIENT_EVIDENCE`, and
  the scan-level verdict is `PASS`, `REVIEW` or `POTENTIAL_VIOLATION`.
  `INSUFFICIENT_EVIDENCE` is a distinct outcome from `FAIL`: "could not be read from this
  photograph" is not a finding that a declaration is absent.
- **Measurement.** Rule 7 letter-height and panel-area measurement, calibrated from a
  reference object in frame (a ₹10 coin) or from artwork DPI. Measurements carry their
  uncertainty, and when the interval straddles a Table-I band edge the rule declines to
  band and returns `REVIEW_REQUIRED` with both uncertainties named, rather than picking a
  side.
- **Catalogue scan.** The same rule set applied to an e-commerce listing's declared fields.
- **Evidence chain.** Every asset and every evaluation appends a hash-linked entry, verified
  on each read. Issuing the report (`json`, `pdf` or `docx`) is itself a chain entry, and is
  refused with 409 until an officer has finalised the review.
- **Officer review.** Jurisdiction-scoped queue (state → region → district), category
  confirmation that re-evaluates the capture as a new scan, and a determination sheet that
  finalises the verdict.
- **Complaints.** A manufacturer complaint raised against a finalised scan, with an
  append-only transition ledger.
- **Vendor self-check.** A vendor submits their own package before shelving it and gets the
  same findings, plus the officer tier the premises routes to.
- **Consumer reviews.** A public per-product safety consensus, looked up by the barcode the
  browser decodes from the photograph or by a typed identifier.
- **Analytics.** Findings by rule, by category, over time, and by jurisdiction, behind a
  GHMC ward choropleth.

Frontend (React 18 + TypeScript + Vite + Tailwind), four route trees mounted side by side:

| Surface | Routes | State |
|---|---|---|
| Officer | queue, verdict detail, new scan, camera capture, vendor submissions, complaints, dashboard | Built |
| Consumer | capture, result, reviews panel | Built |
| Vendor | login, scan, result | Built |
| Admin | `/admin` | Scaffold only — no screens |

## What is not built

- **The admin surface has no screens.** RBAC administration, scheduled crawling and
  manufacturer self-check (F31–F38) are routed and empty.
- **No PDP-trained detector.** `PDP_WEIGHTS_PATH` is deliberately unset. Principal display
  panel area comes from the officer's own drag over the photograph, or is not measured at
  all; pointing the setting at stock COCO weights would return a confident wrong box and
  feed its area to the Rule 7 band lookup.
- **No copilot.** The clause-retrieval assistant in ARCHITECTURE.md is a design, not code.
- **No queue worker.** `redis` is in the production stack, but nothing in the backend is a
  client of it; scans are evaluated in the request's own background task.
- **MinIO is optional.** With the four `EVIDENCE_S3_*` settings unset, captures stay on the
  backend's local disk.
- **Cloud OCR is off**, with a daily page cap of `0`. Turning it on is a deliberate act.

## Run it

Requires Docker with the Compose plugin. The backend image downloads and bakes in the OCR
weights during the build, so the running stack fetches no model at runtime.

```bash
git clone https://github.com/SIH-2026-CSM-A/26034.git
cd 26034
cp .env.example .env          # then fill in every placeholder
docker compose -f docker-compose.prod.yml up -d --build
```

Three values in `.env` have no working default:

- `POSTGRES_PASSWORD` and `MINIO_ROOT_PASSWORD` — any generated password (MinIO needs ≥ 8
  characters).
- `JWT_SECRET` — at least 32 characters; the app refuses to start below that.
  `openssl rand -hex 32`.
- `OFFICERS` — a JSON array of the accounts that may sign in, each with a bcrypt
  `password_hash` (never a password) and a jurisdiction. It ships as `[]`, which means no
  one can sign in. Produce a hash with `app.core.auth.hash_password`.

Leave `VITE_API_BASE_URL=/api`. nginx in the frontend image proxies `/api` to the backend
over the Compose network, so the bundle and the API share one origin and no CORS is
configured anywhere.

The backend runs `alembic upgrade head` on startup. When the stack is healthy:

| | |
|---|---|
| Officer surface | <http://localhost/login> |
| Consumer surface | <http://localhost/consumer> |
| API schema | <http://localhost:8000/docs> |

The database publishes on host port **5433**, not 5432 — a local PostgreSQL cluster on
5432 silently wins over a container published there, and Alembic then migrates the wrong
server.

## Architecture

One FastAPI application over PostgreSQL 16, one React bundle served by nginx, one Compose
project on one VM. The backend is a set of independent vertical modules — `vision`,
`extraction`, `measurement`, `rules`, `evidence`, `tamper`, `reviews`, `complaints`,
`vendor`, `analytics` — none of which imports another: a module may import `app.contracts`
(the shared types, which import nothing) and `app.core` (settings, session, auth,
jurisdiction) and nothing else, and `app.pipeline` is the only package permitted to compose
them. That boundary is enforced by `import-linter` in CI rather than by convention. A
submission is committed before any vision runs, the pipeline then evaluates with no
transaction open — PaddleOCR would otherwise hold a pool connection for the better part of
a minute — and the verdict and its findings are written together in one atomic block, so a
crash leaves a scan visibly unevaluated rather than half-judged. The rule parameters in
force at evaluation time are snapshotted into the verdict record instead of joined from the
rules table, so replaying an old verdict shows what the officer actually saw and not what
today's corpus says.

## Repository map

| Path | Holds |
|---|---|
| `bck/app/contracts/` | Shared types crossing module boundaries. Imports nothing. |
| `bck/app/core/` | Settings, database session, auth, RBAC, jurisdiction scoping. |
| `bck/app/modules/` | One vertical slice per capability. Modules never import each other. |
| `bck/app/pipeline/` | The only place modules are composed; the scan endpoints. |
| `bck/alembic/` | Migrations, run on backend startup. |
| `fnt/src/` | The four route trees: `officer/`, `consumer/`, `vendor/`, `admin/`. |
| `rules-corpus/` | The source gazettes every encoded rule cites. Immutable. |
| `datasets/` | Annotated evaluation captures. |
| `demo/` | The recording script and its per-step index. |

[ARCHITECTURE.md](ARCHITECTURE.md) has the stack decisions and what was rejected.
Contributors start at [SETUP.md](SETUP.md) and [AGENTS.md](AGENTS.md).
