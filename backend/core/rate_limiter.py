"""Simple IP-based rate limiter for FastAPI using Depends."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class _RateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(self):
        # {(ip, path): [timestamp, ...]}
        self._requests: dict[tuple, list[float]] = defaultdict(list)

    def _clean(self, key: tuple, window: int):
        cutoff = time.time() - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check(self, ip: str, path: str, max_requests: int, window: int = 60):
        """Raise 429 if rate limit exceeded. Default window is 60 seconds."""
        key = (ip, path)
        self._clean(key, window)
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
