"""A sliding-window request limit for the routes that have no login to lean on.

The consumer upload is unauthenticated by design and queues an OCR run of the better part
of a minute, so one unthrottled client can occupy the evaluator indefinitely and hold a
decoded frame in memory for every request it has queued. Two windows close that: one per
client, and one across all clients, because the client key is a request header behind a
proxy and a header is something a caller can vary.

Both limits are deployment decisions and live in :class:`app.core.config.Settings`.

# ponytail: in-process state. The deployment runs one uvicorn worker, so one process sees
# every request. A second worker would give each its own window; the upgrade is the same
# two counters in Redis, which is already in the stack.
"""

import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

WINDOW_SECONDS = 60.0
"""The span both limits are counted over. The settings are named per-minute to match."""

CLIENT_ADDRESS_HEADERS = ("cf-connecting-ip", "x-real-ip")
"""Where the caller's address is, in the order trusted.

``CF-Connecting-IP`` is overwritten by Cloudflare at the tunnel edge, so a caller cannot
supply their own through it. ``X-Real-IP`` is what ``fnt/nginx.conf`` sets from the socket
it accepted. ``X-Forwarded-For`` is deliberately absent: every hop appends to it and the
first entry is whatever the caller typed.
"""

MAX_TRACKED_CLIENTS = 10_000
"""A bound on the per-client table, so the limiter cannot itself be grown without limit by
a caller cycling addresses. At the bound, clients with no request left inside the window
are dropped; the global window is what holds while the table is under that pressure."""


def client_key(request: Request) -> str:
    """The best available identity for the caller of ``request``."""
    for header in CLIENT_ADDRESS_HEADERS:
        value = request.headers.get(header, "").strip()
        if value:
            return value
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Counts requests per client and in total over the trailing window."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._by_client: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()

    def _trim(self, stamps: deque[float], now: float) -> None:
        while stamps and now - stamps[0] >= WINDOW_SECONDS:
            stamps.popleft()

    def retry_after(self, key: str, *, per_client: int, overall: int) -> int | None:
        """Record one request, or return the seconds to wait if it is over a limit.

        A refused request is not recorded: a client hammering a closed door does not push
        its own reopening further away, and does not consume the global window either.
        """
        now = self._clock()
        self._trim(self._all, now)
        stamps = self._by_client.setdefault(key, deque())
        self._trim(stamps, now)

        blocking = [
            window[0]
            for window, limit in ((stamps, per_client), (self._all, overall))
            if len(window) >= limit
        ]
        if blocking:
            if not stamps:
                del self._by_client[key]
            return max(1, int(max(blocking) + WINDOW_SECONDS - now) + 1)

        if len(self._by_client) > MAX_TRACKED_CLIENTS:
            for other in [k for k, v in self._by_client.items() if k != key]:
                self._trim(self._by_client[other], now)
                if not self._by_client[other]:
                    del self._by_client[other]
        stamps.append(now)
        self._all.append(now)
        return None


consumer_scan_limiter = SlidingWindowLimiter()
"""The one limiter instance behind :func:`limit_consumer_scans`."""


def limit_consumer_scans(request: Request) -> None:
    """FastAPI dependency: a 429 with ``Retry-After`` once the consumer upload is over limit.

    Runs before anything is decoded, stored or queued. It does not run before the upload
    is received: FastAPI parses a multipart body ahead of resolving dependencies, so the
    size of what arrives is bounded by the proxy's ``client_max_body_size``, not here.
    """
    settings = get_settings()
    wait = consumer_scan_limiter.retry_after(
        client_key(request),
        per_client=settings.consumer_scans_per_client_per_minute,
        overall=settings.consumer_scans_per_minute,
    )
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many scans submitted; wait before submitting another",
            headers={"Retry-After": str(wait)},
        )
