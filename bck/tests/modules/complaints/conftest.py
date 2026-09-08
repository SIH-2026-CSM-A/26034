"""Fixtures for the complaint endpoints.

The scan endpoints' fixtures are exactly what these tests need — the same mapped schema, the
same real application driven over ASGI, the same genuinely signed tokens — so they are
imported rather than copied. A second copy would be a second thing to keep in step with the
schema, and the two would disagree silently rather than fail.
"""

from tests.pipeline.conftest import (  # noqa: F401
    client,
    configured,
    isolated_settings,
    schema,
)
