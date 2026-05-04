"""Slow-request alert middleware (Module 18 exercise)."""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.request_id import get_request_id

logger = logging.getLogger("http.slow")


class SlowRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        if duration_ms > settings.slow_request_ms:
            logger.warning(
                "SLOW: %s %s took %.1fms (threshold %dms)",
                request.method,
                request.url.path,
                duration_ms,
                settings.slow_request_ms,
                extra={
                    "request_id": get_request_id(),
                    "duration_ms": round(duration_ms, 1),
                },
            )
        return response
