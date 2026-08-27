"""Dependency-free, in-process sliding-window rate limiter.

FastAPI dependency factory that returns HTTP 429 when a client exceeds a
per-minute cap. Deterministic per (client-ip) key with a module-level lock so
the counting is consistent across FastAPI's sync route threadpool.
"""

import threading
import time

from fastapi import HTTPException, Request, status

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limit: int, window: float = 60.0):
    """Return a FastAPI dependency enforcing ``limit`` requests per ``window``s."""

    def dependency(request: Request) -> None:
        key = _client_key(request)
        now = time.monotonic()
        with _lock:
            recent = [t for t in _hits.get(key, []) if now - t < window]
            if len(recent) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down and try again.",
                )
            recent.append(now)
            _hits[key] = recent

    return dependency