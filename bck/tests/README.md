# tests

**Owner:** shared — a module's tests are owned by that module's owner

Mirror the package layout: `tests/modules/vision/` for `app/modules/vision/`. Tests for
a module may import that module; they follow the same independence rule as the code.

`test_import_boundaries.py` is the exception — it belongs to the whole repo and guards
the `lint-imports` configuration itself.

Run with `uv run pytest` from `bck/`.
