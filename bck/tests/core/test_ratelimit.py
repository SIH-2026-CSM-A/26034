"""The sliding-window limiter, on a clock the test owns."""

from starlette.requests import Request

from app.core.ratelimit import WINDOW_SECONDS, SlidingWindowLimiter, client_key


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _request(headers: dict[str, str], peer: str = "10.0.0.9") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": (peer, 1234)})


def test_a_client_is_refused_past_its_limit_and_admitted_once_the_window_slides() -> None:
    clock = _Clock()
    limiter = SlidingWindowLimiter(clock)
    assert limiter.retry_after("a", per_client=2, overall=100) is None
    clock.now += 10
    assert limiter.retry_after("a", per_client=2, overall=100) is None
    wait = limiter.retry_after("a", per_client=2, overall=100)
    assert wait is not None and 50 <= wait <= 51

    clock.now += WINDOW_SECONDS - 10
    assert limiter.retry_after("a", per_client=2, overall=100) is None


def test_one_clients_limit_does_not_refuse_another() -> None:
    limiter = SlidingWindowLimiter(_Clock())
    assert limiter.retry_after("a", per_client=1, overall=100) is None
    assert limiter.retry_after("a", per_client=1, overall=100) is not None
    assert limiter.retry_after("b", per_client=1, overall=100) is None


def test_the_overall_limit_holds_against_a_caller_cycling_addresses() -> None:
    limiter = SlidingWindowLimiter(_Clock())
    for index in range(3):
        assert limiter.retry_after(f"client-{index}", per_client=5, overall=3) is None
    assert limiter.retry_after("client-new", per_client=5, overall=3) is not None


def test_a_refused_request_does_not_extend_the_wait() -> None:
    clock = _Clock()
    limiter = SlidingWindowLimiter(clock)
    assert limiter.retry_after("a", per_client=1, overall=100) is None
    for _ in range(20):
        clock.now += 1
        assert limiter.retry_after("a", per_client=1, overall=100) is not None
    clock.now += WINDOW_SECONDS - 20
    assert limiter.retry_after("a", per_client=1, overall=100) is None


def test_the_client_key_ignores_x_forwarded_for() -> None:
    """The first X-Forwarded-For entry is whatever the caller typed; it must not be the key."""
    spoofed = _request({"X-Forwarded-For": "1.2.3.4", "X-Real-IP": "172.18.0.1"})
    assert client_key(spoofed) == "172.18.0.1"
    assert client_key(_request({"CF-Connecting-IP": "203.0.113.7", "X-Real-IP": "172.18.0.1"})) == (
        "203.0.113.7"
    )
    assert client_key(_request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.9"
