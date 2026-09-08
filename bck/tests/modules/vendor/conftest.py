"""Fixtures for the vendor register endpoints.

The scan endpoints' fixtures are exactly what these tests need — the same mapped schema, the
same real application driven over ASGI, the same genuinely signed tokens — so they are
imported rather than copied. A second copy would be a second thing to keep in step with the
schema, and the two would disagree silently rather than fail.

The rest of this package tests pure domain, service and repository code against mocks; those
tests take none of these fixtures and are unaffected by them, apart from ``isolated_settings``,
which is autouse and only keeps a developer's own ``.env`` out of the run.
"""

from tests.pipeline.conftest import (  # noqa: F401
    client,
    configured,
    isolated_settings,
    schema,
)
