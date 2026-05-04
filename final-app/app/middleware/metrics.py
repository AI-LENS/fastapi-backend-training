"""Prometheus metrics middleware (Module 21)."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        # The full URL would explode cardinality; use the path template as label
        path = request.url.path
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.perf_counter() - start
            http_requests_total.labels(
                method=request.method, path=path, status=str(status)
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method, path=path
            ).observe(duration)
        return response
