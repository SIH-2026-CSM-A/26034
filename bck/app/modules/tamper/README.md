# Tamper

**Owner:** @adepushivasai901-ops

Flags images that have been edited, spliced, or re-compressed, so a clean verdict is not issued on a doctored label.

## Layout

Layers live inside this package, not above it:

| File | Holds |
|---|---|
| `router.py` | FastAPI routes. Thin — parse in, delegate, return out. |
| `service.py` | Business logic. Testable without HTTP or a database. |
| `repository.py` | Every database query this module makes. |
| `schemas.py` | Pydantic request/response DTOs for this module's routes. |

Split a file once it passes 300 lines rather than letting it grow.

## Imports

This module may import `app.contracts`, `app.core`, and itself. Nothing else.

Importing another module under `app.modules` — or anything under `app.pipeline` —
fails `lint-imports` in CI. If you need something another module has, the shared type
belongs in `app.contracts` and the composition belongs in `app.pipeline`.
