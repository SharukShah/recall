"""Simple IP-based rate limiter for FastAPI using Depends."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class _RateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(self):
        # {(ip, path): [timestamp, ...]}
        self._requests: dict[tuple, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _clean(self, key: tuple, window: int):
        cutoff = time.time() - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def _periodic_cleanup(self, window: int):
        """Remove empty keys every 5 minutes to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        cutoff = now - window
        empty_keys = [
            k for k, v in self._requests.items()
            if not v or all(t <= cutoff for t in v)
        ]
        for k in empty_keys:
            del self._requests[k]

    def check(self, ip: str, path: str, max_requests: int, window: int = 60):
        """Raise 429 if rate limit exceeded. Default window is 60 seconds."""
        key = (ip, path)
        self._clean(key, window)
        self._periodic_cleanup(window)
        if len(self._requests[key]) >= max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self._requests[key].append(time.time())


_limiter = _RateLimiter()


def rate_limit(max_requests: int, window: int = 60):
    """FastAPI dependency for rate limiting. Usage: dependencies=[Depends(rate_limit(10))]"""
    async def dependency(request: Request):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        _limiter.check(ip, path, max_requests, window)
    return dependency
