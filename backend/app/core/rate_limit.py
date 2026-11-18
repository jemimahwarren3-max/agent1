"""In-process rate limiting for auth endpoints (login/register are the
brute-force/signup-spam surface). Single-process, in-memory — same limitation
as the Phase 3 BackgroundTasks note: a real deployment with multiple API
processes needs this backed by Redis (already configured via REDIS_URL, not
yet wired to anything) instead of a module-level dict."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 10

_hits: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def reset() -> None:
    """Test-only: clears all tracked hit history."""
    _hits.clear()


def rate_limit_auth(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    recent = [t for t in _hits[key] if now - t < _WINDOW_SECONDS]
    if len(recent) >= _MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many attempts — try again in a minute.")
    recent.append(now)
    _hits[key] = recent
